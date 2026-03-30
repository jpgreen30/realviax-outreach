"""
Video generator for teaser and full videos using ffmpeg
"""
import os
import json
import logging
import subprocess
import requests
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

class VideoGenerator:
    def __init__(
        self,
        logo_path: str,
        music_dir: str,
        output_dir: str,
        template_teaser: Optional[str] = None,
        template_full: Optional[str] = None
    ):
        self.logo_path = logo_path
        self.music_dir = music_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load templates if provided
        self.template_teaser = self._load_template(template_teaser) if template_teaser else self._default_teaser_template()
        self.template_full = self._load_template(template_full) if template_full else self._default_full_template()
        
        # Ensure assets exist
        if not os.path.exists(logo_path):
            logger.warning(f"Logo not found at {logo_path}. Watermark will be skipped.")
    
    def _load_template(self, path: str) -> Dict:
        with open(path, 'r') as f:
            return json.load(f)
    
    def _default_teaser_template(self) -> Dict:
        return {
            "duration": 30,
            "scene_duration": 6,
            "fps": 30,
            "bitrate": "5000k",
            "zoom_factor": 0.15,
            "text_size": {"scene": 60, "info": 70},
            "info_position": 0.85,  # fraction from top for info text
            "scene_label_position": 0.7  # fraction from top for scene label
        }
    
    def _default_full_template(self) -> Dict:
        return {
            "duration": 60,
            "scene_duration": 8,  # 7-8 scenes
            "fps": 30,
            "bitrate": "8000k",
            "zoom_factor": 0.12,
            "text_size": {"scene": 80, "info": 90},
            "info_position": 0.85,
            "scene_label_position": 0.7
        }
    
    def download_photos(self, photo_urls: List[str], output_dir: str) -> List[str]:
        """Download photos to local directory for processing"""
        os.makedirs(output_dir, exist_ok=True)
        local_paths = []
        
        for i, url in enumerate(photo_urls):
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    path = os.path.join(output_dir, f"photo_{i:02d}.jpg")
                    with open(path, 'wb') as f:
                        f.write(response.content)
                    local_paths.append(path)
                    logger.debug(f"Downloaded photo {i}: {path}")
                else:
                    logger.warning(f"Failed to download {url}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
        
        return local_paths
    
    def prepare_scene_images(
        self,
        photo_paths: List[str],
        template: Dict,
        listing_data: Dict,
        output_dir: str
    ) -> List[str]:
        """Create scene images with text overlays and proper cropping"""
        os.makedirs(output_dir, exist_ok=True)
        
        W, H = 1080, 1920
        scene_duration = template["scene_duration"]
        total_scenes = int(template["duration"] / scene_duration)
        
        # Info texts to display (overlapping across scenes)
        info_texts = []
        price = listing_data.get("price", "")
        if price:
            price_str = f"${price:,.0f}" if isinstance(price, (int, float)) else str(price)
            info_texts.append((0, 5, price_str))
        
        address = listing_data.get("address", "")
        if address:
            info_texts.append((5, 10, address))
        
        beds = listing_data.get("beds", "")
        baths = listing_data.get("baths", "")
        sqft = listing_data.get("sqft", "")
        if beds or baths or sqft:
            specs = f"{beds} bed | {baths} bath | {sqft} sqft" if sqft else f"{beds} bed | {baths} bath"
            info_texts.append((10, 15, specs))
        
        tagline = listing_data.get("tagline", "Luxury living at its finest")
        info_texts.append((15, 20, tagline))
        
        cta = "Schedule a viewing → realviax.com"
        info_texts.append((20, template["duration"], cta))
        
        # Scene labels (can be generic or from listing)
        default_labels = ["Exterior", "Interior", "Living Space", "Kitchen", "Bedroom", "Bathroom", "Details", "Aerial"]
        scene_labels = listing_data.get("scene_labels", default_labels[:total_scenes])
        
        # Create scene images
        scene_paths = []
        for scene_idx in range(total_scenes):
            # Select a photo (cycle through available ones)
            photo_idx = scene_idx % len(photo_paths) if photo_paths else None
            if photo_idx is not None:
                img = Image.open(photo_paths[photo_idx])
                # Crop/scale to 1080x1920 covering
                img = self._cover_crop(img, W, H)
            else:
                # Fallback: solid color with text only
                img = Image.new('RGB', (W, H), color=(99, 102, 241))
            
            draw = ImageDraw.Draw(img)
            
            # Draw scene label at top
            label = scene_labels[scene_idx] if scene_idx < len(scene_labels) else f"Scene {scene_idx+1}"
            self._draw_text_with_shadow(draw, W/2, H/2 - 400, label, size=template["text_size"]["scene"])
            
            # Draw info texts that should be visible during this scene
            scene_start = scene_idx * scene_duration
            scene_end = scene_start + scene_duration
            for start, end, txt in info_texts:
                if start < scene_end and end > scene_start:
                    y = int(H * template["info_position"])
                    self._draw_text_with_shadow(draw, W/2, y, txt, size=template["text_size"]["info"])
            
            out_path = os.path.join(output_dir, f"scene_{scene_idx:03d}.jpg")
            img.save(out_path, quality=95)
            scene_paths.append(out_path)
            logger.debug(f"Created scene {scene_idx}: {out_path}")
        
        return scene_paths
    
    def _cover_crop(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Crop image to cover target dimensions, centered"""
        img_ratio = img.width / img.height
        target_ratio = target_w / target_h
        
        if img_ratio > target_ratio:
            # Wider, crop sides
            new_h = target_h
            new_w = int(img.width * (target_h / img.height))
        else:
            # Taller, crop top/bottom
            new_w = target_w
            new_h = int(img.height * (target_w / img.width))
        
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        return img_resized.crop((left, top, left + target_w, top + target_h))
    
    def _draw_text_with_shadow(self, draw: ImageDraw.Draw, x, y, text: str, size: int = 60, color: str = "white"):
        """Draw text with black shadow for readability"""
        # Convert to int for positioning
        x, y = int(x), int(y)
        draw.text((x + 3, y + 3), text, fill='black', anchor="mm", font=None, size=size)
        draw.text((x, y), text, fill='white', anchor="mm", font=None, size=size)
    
    def render_video(
        self,
        scene_paths: List[str],
        output_path: str,
        template: Dict,
        listing_data: Optional[Dict] = None
    ) -> str:
        """Render final video using ffmpeg"""
        
        # Build ffmpeg inputs
        inputs = []
        for path in scene_paths:
            inputs.extend(['-loop', '1', '-t', str(template["scene_duration"]), '-i', path])
        
        # Logo overlay
        if os.path.exists(self.logo_path):
            inputs.extend(['-loop', '1', '-i', self.logo_path])
            logo_index = len(scene_paths)
        else:
            logo_index = None
        
        # Music - find appropriate file
        music_file = self._select_music(template["duration"])
        if music_file:
            inputs.extend(['-i', music_file])
            music_index = len(scene_paths) + (1 if logo_index else 0)
        else:
            music_index = None
        
        # Build filter complex
        filter_parts = []
        # Zoompan for each scene
        for i in range(len(scene_paths)):
            zoom_expr = f"1+{template['zoom_factor']}*on/({template['scene_duration']}*{template['fps']})"
            filter_parts.append(
                f"[{i}:v]zoompan=z='{zoom_expr}':d={template['scene_duration']*template['fps']}:s=1080x1920,framerate={template['fps']}[v{i}]"
            )
        
        # Concat scenes
        concat_inputs = ' '.join([f'[v{i}]' for i in range(len(scene_paths))])
        filter_parts.append(f"{concat_inputs}concat=n={len(scene_paths)}:v=1:a=0[vidnoaudio]")
        
        # Overlay logo
        if logo_index is not None:
            filter_parts.append(
                f"[vidnoaudio][{logo_index}:v]overlay=W-w-20:H-h-20:enable='between(t,0,{template['duration']})'[viddated]"
            )
            final_video = "[viddated]"
        else:
            final_video = "[vidnoaudio]"
        
        # Format and audio mapping
        filter_parts.append(f"{final_video}format=yuv420p[vid]")
        filter_complex = ';'.join(filter_parts)
        
        # Build output args
        output_args = [
            '-map', '[vid]'
        ]
        if music_index is not None:
            output_args.extend(['-map', f'{music_index}:a'])
        output_args.extend([
            '-t', str(template["duration"]),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-b:v', template["bitrate"],
            '-c:a', 'aac' if music_index else 'none',
            '-b:a', '192k' if music_index else None,
            '-r', str(template["fps"]),
            '-pix_fmt', 'yuv420p'
        ])
        # Remove None values
        output_args = [a for a in output_args if a is not None]
        
        # Build command
        cmd = ['ffmpeg', '-y'] + inputs + ['-filter_complex', filter_complex] + output_args + [output_path]
        
        logger.info(f"Rendering video: {output_path}")
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Video rendering failed: {result.stderr}")
        
        logger.info(f"Video rendered successfully: {output_path}")
        return output_path
    
    def _select_music(self, duration: int) -> Optional[str]:
        """Select a music file matching duration (or closest)"""
        if not os.path.exists(self.music_dir):
            return None
        
        music_files = [f for f in os.listdir(self.music_dir) if f.endswith('.mp3')]
        if not music_files:
            return None
        
        # For simplicity, pick first file (or find file with > duration)
        for f in music_files:
            path = os.path.join(self.music_dir, f)
            # Could check duration via ffprobe, but just use first available
            return path
        return None
    
    def generate_teaser(
        self,
        listing_data: Dict,
        photo_urls: List[str],
        custom_text: Optional[Dict] = None
    ) -> str:
        """Generate a 30-second teaser video"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(self.output_dir / f"teaser_{timestamp}.mp4")
        
        # Working directory for this render
        work_dir = self.output_dir / f"work_{timestamp}"
        work_dir.mkdir()
        
        # Download photos
        logger.info("Downloading photos...")
        photo_paths = self.download_photos(photo_urls, str(work_dir / "photos"))
        
        if not photo_paths:
            raise ValueError("No photos could be downloaded")
        
        # Prepare scene images with text
        logger.info("Preparing scene images...")
        scene_paths = self.prepare_scene_images(
            photo_paths,
            self.template_teaser,
            listing_data,
            str(work_dir / "scenes")
        )
        
        # Render video
        logger.info("Rendering teaser video...")
        return self.render_video(scene_paths, output_path, self.template_teaser, listing_data)
    
    def generate_full(
        self,
        listing_data: Dict,
        photo_urls: List[str],
        duration: int = 60
    ) -> str:
        """Generate a full-length (60s) video"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(self.output_dir / f"full_{timestamp}.mp4")
        
        work_dir = self.output_dir / f"work_{timestamp}"
        work_dir.mkdir()
        
        photo_paths = self.download_photos(photo_urls, str(work_dir / "photos"))
        if not photo_paths:
            raise ValueError("No photos could be downloaded")
        
        # Adjust template for 60s
        full_template = self.template_full.copy()
        full_template["duration"] = duration
        full_template["scene_duration"] = duration / max(8, min(12, len(photo_paths)))
        
        scene_paths = self.prepare_scene_images(
            photo_paths,
            full_template,
            listing_data,
            str(work_dir / "scenes")
        )
        
        logger.info("Rendering full video...")
        return self.render_video(scene_paths, output_path, full_template, listing_data)