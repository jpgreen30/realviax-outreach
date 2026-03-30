"""
Full-featured video generator for teaser and full videos using ffmpeg.
"""
import os
import json
import logging
import subprocess
import shutil
import requests
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings

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
        
        self.template_teaser = self._default_teaser_template()
        self.template_full = self._default_full_template()
        
        if not os.path.exists(logo_path):
            logger.warning(f"Logo not found at {logo_path}. Watermark will be skipped.")
    
    def _default_teaser_template(self) -> Dict:
        return {
            "duration": 30,
            "scene_duration": 6,
            "fps": 30,
            "bitrate": "5000k",
            "zoom_factor": 0.15,
            "text_size": {"scene": 60, "info": 70},
            "info_position": 0.85,
            "scene_label_position": 0.7
        }
    
    def _default_full_template(self) -> Dict:
        return {
            "duration": 60,
            "scene_duration": 8,
            "fps": 30,
            "bitrate": "8000k",
            "zoom_factor": 0.12,
            "text_size": {"scene": 80, "info": 90},
            "info_position": 0.85,
            "scene_label_position": 0.7
        }
    
    def download_photos(self, photo_urls: List[str], output_dir: str) -> List[str]:
        os.makedirs(output_dir, exist_ok=True)
        local_paths = []
        headers = {"User-Agent": "Mozilla/5.0"}
        for i, url in enumerate(photo_urls):
            try:
                if url.startswith("file://"):
                    src_path = url[7:]
                    if os.path.exists(src_path):
                        dest_path = os.path.join(output_dir, f"photo_{i:02d}.jpg")
                        shutil.copy2(src_path, dest_path)
                        local_paths.append(dest_path)
                else:
                    resp = requests.get(url, headers=headers, timeout=30)
                    if resp.status_code == 200:
                        path = os.path.join(output_dir, f"photo_{i:02d}.jpg")
                        with open(path, 'wb') as f:
                            f.write(resp.content)
                        local_paths.append(path)
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
        os.makedirs(output_dir, exist_ok=True)
        W, H = 1080, 1920
        scene_duration = template["scene_duration"]
        total_scenes = int(template["duration"] / scene_duration)
        
        info_texts = []
        price = listing_data.get("price", "")
        if price:
            if isinstance(price, (int, float)):
                price_str = f"${price:,.0f}"
            else:
                price_str = str(price)
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
        
        default_labels = ["Exterior", "Interior", "Living Space", "Kitchen", "Bedroom", "Bathroom", "Details", "Aerial"]
        scene_labels = listing_data.get("scene_labels", default_labels[:total_scenes])
        
        scene_paths = []
        for scene_idx in range(total_scenes):
            photo_idx = scene_idx % len(photo_paths) if photo_paths else None
            if photo_idx is not None:
                img = Image.open(photo_paths[photo_idx])
                img = self._cover_crop(img, W, H)
            else:
                img = Image.new('RGB', (W, H), color=(26, 26, 46))
            
            draw = ImageDraw.Draw(img)
            label = scene_labels[scene_idx] if scene_idx < len(scene_labels) else f"Scene {scene_idx+1}"
            self._draw_text_with_shadow(draw, W/2, H * 0.3, label, size=template["text_size"]["scene"])
            
            scene_start = scene_idx * scene_duration
            scene_end = scene_start + scene_duration
            for start_sec, end_sec, txt in info_texts:
                if scene_start < end_sec and start_sec < scene_end:
                    x = W/2
                    y = H * 0.5 + (info_texts.index((start_sec,end_sec,txt)) * 80)
                    self._draw_text_with_shadow(draw, x, y, txt, size=template["text_size"]["info"])
            
            out_path = os.path.join(output_dir, f"scene_{scene_idx:03d}.jpg")
            img.save(out_path, quality=90)
            scene_paths.append(out_path)
        
        return scene_paths
    
    def _cover_crop(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        img_ratio = img.width / img.height
        target_ratio = target_w / target_h
        if img_ratio > target_ratio:
            new_h = target_h
            new_w = int(img.width * (target_h / img.height))
        else:
            new_w = target_w
            new_h = int(img.height * (target_w / img.width))
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        return img_resized.crop((left, top, left + target_w, top + target_h))
    
    def _draw_text_with_shadow(self, draw: ImageDraw.Draw, x, y, text: str, size: int = 60, color: str = "white"):
        x, y = int(x), int(y)
        draw.text((x + 3, y + 3), text, fill='black', anchor="mm", size=size)
        draw.text((x, y), text, fill='white', anchor="mm", size=size)
    
    def render_video(
        self,
        scene_paths: List[str],
        output_path: str,
        template: Dict,
        listing_data: Optional[Dict] = None
    ) -> str:
        inputs = []
        for path in scene_paths:
            inputs.extend(['-loop', '1', '-t', str(template["scene_duration"]), '-i', path])
        
        if os.path.exists(self.logo_path):
            inputs.extend(['-loop', '1', '-i', self.logo_path])
            logo_index = len(scene_paths)
        else:
            logo_index = None
        
        music_file = self._select_music(template["duration"])
        if music_file:
            inputs.extend(['-i', music_file])
            music_index = len(scene_paths) + (1 if logo_index else 0)
        else:
            music_index = None
        
        filter_parts = []
        scene_frames = int(template["scene_duration"] * template["fps"])
        for i in range(len(scene_paths)):
            zoom_expr = f"1+{template['zoom_factor']}*on/({template['scene_duration']}*{template['fps']})"
            filter_parts.append(
                f"[{i}:v]zoompan=z='{zoom_expr}':d={scene_frames}:s=1080x1920,framerate={template['fps']}[v{i}]"
            )
        
        concat_inputs = ' '.join([f'[v{i}]' for i in range(len(scene_paths))])
        filter_parts.append(f"{concat_inputs}concat=n={len(scene_paths)}:v=1:a=0[vidnoaudio]")
        
        if logo_index is not None:
            filter_parts.append(
                f"[vidnoaudio][{logo_index}:v]overlay=W-w-20:H-h-20:enable='between(t,0,{template['duration']})'[viddated]"
            )
            final_video = "[viddated]"
        else:
            final_video = "[vidnoaudio]"
        
        filter_parts.append(f"{final_video}format=yuv420p[vid]")
        filter_complex = ';'.join(filter_parts)
        
        output_args = ['-map', '[vid]']
        if music_index is not None:
            output_args.extend(['-map', f'{music_index}:a'])
        output_args.extend([
            '-t', str(template["duration"]),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-b:v', template["bitrate"],
            '-c:a', 'aac' if music_index else None,
            '-b:a', '192k' if music_index else None,
            '-r', str(template["fps"]),
            '-pix_fmt', 'yuv420p'
        ])
        output_args = [a for a in output_args if a is not None]
        
        cmd = ['ffmpeg', '-y'] + inputs + ['-filter_complex', filter_complex] + output_args + [output_path]
        logger.info(f"Generating video: {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Video rendering failed: {result.stderr}")
        return output_path
    
    def _select_music(self, duration: int) -> Optional[str]:
        if not os.path.exists(self.music_dir):
            return None
        music_files = [f for f in os.listdir(self.music_dir) if f.endswith('.mp3')]
        if not music_files:
            return None
        return os.path.join(self.music_dir, music_files[0])
    
    def generate_teaser(self, lead_id: int, photo_urls: List[str], listing_data: dict, **kwargs) -> str:
        output_path = self.output_dir / f"lead_{lead_id}_teaser.mp4"
        if output_path.exists():
            return str(output_path)
        work_dir = self.output_dir / f"work_{lead_id}_teaser"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir()
        photos = self.download_photos(photo_urls, str(work_dir / "photos"))
        if not photos:
            raise ValueError("No photos downloaded")
        # Merge style overrides
        template = {**self.template_teaser, **kwargs}
        scenes = self.prepare_scene_images(photos, template, listing_data, str(work_dir / "scenes"))
        return self.render_video(scenes, str(output_path), template, listing_data)
    
    def generate_full(self, lead_id: int, photo_urls: List[str], listing_data: dict, duration: int = 60, **kwargs) -> str:
        output_path = self.output_dir / f"lead_{lead_id}_full.mp4"
        if output_path.exists():
            return str(output_path)
        work_dir = self.output_dir / f"work_{lead_id}_full"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir()
        photos = self.download_photos(photo_urls, str(work_dir / "photos"))
        if not photos:
            raise ValueError("No photos downloaded")
        full_template = {**self.template_full, "duration": duration}
        total_scenes = max(8, min(12, len(photos)))
        full_template["scene_duration"] = full_template["duration"] / total_scenes
        full_template.update(kwargs)
        scenes = self.prepare_scene_images(photos, full_template, listing_data, str(work_dir / "scenes"))
        return self.render_video(scenes, str(output_path), full_template, listing_data)

# Singleton instance using settings
video_gen = VideoGenerator(
    logo_path=settings.LOGO_PATH,
    music_dir=settings.MUSIC_DIR,
    output_dir=settings.VIDEO_OUTPUT_DIR
)
