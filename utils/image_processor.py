from PIL import Image, ImageDraw, ImageFont
import re
from typing import List, Tuple
import io
import base64

def natural_sort_key(s: str) -> List[str]:
    """Sort strings containing numbers in natural order."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def add_text_to_image(draw: ImageDraw, text: str, position: Tuple[int, int], size: int) -> None:
    """Add text to image with proper font size and background."""
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox(position, text, font=font)
    padding = 10
    background_bbox = (
        bbox[0] - padding,
        bbox[1] - padding,
        bbox[2] + padding,
        bbox[3] + padding
    )
    draw.rectangle(background_bbox, fill=(0, 0, 0, 128))
    draw.text(position, text, fill="white", font=font)

def merge_images(images: List[Image.Image], count: int) -> Image.Image:
    """Merge multiple images based on count."""
    if count < 2 or count > 6:
        raise ValueError("Image count must be between 2 and 6")
    
    # Convert all images to RGBA
    images = [img.convert('RGBA') for img in images]
    
    if count == 2:
        return merge_two_images(images)
    elif count == 3:
        return merge_three_images(images)
    elif count == 4:
        return merge_four_images(images)
    else:  # 5 or 6 images
        return merge_grid_images(images, 2, 3)

def merge_two_images(images: List[Image.Image]) -> Image.Image:
    """Merge two images horizontally."""
    # Resize images to same height
    target_height = max(img.size[1] for img in images)
    ratios = [target_height / img.size[1] for img in images]
    new_widths = [int(img.size[0] * ratio) for img in ratios]
    
    resized_images = [img.resize((new_width, target_height), Image.Resampling.LANCZOS)
                     for img, new_width in zip(images, new_widths)]
    
    # Create new image
    new_width = sum(new_widths)
    merged = Image.new('RGBA', (new_width, target_height), (0, 0, 0, 0))
    
    # Paste images
    x_offset = 0
    for i, img in enumerate(resized_images):
        merged.paste(img, (x_offset, 0))
        
        # Add text
        draw = ImageDraw.Draw(merged)
        text_size = int(target_height * 0.05)
        text = f"图片 {i+1}"
        add_text_to_image(draw, text, (x_offset + 20, 20), text_size)
        
        x_offset += img.size[0]
    
    return merged

def merge_three_images(images: List[Image.Image]) -> Image.Image:
    """Merge three images vertically."""
    # Resize images to same width
    target_width = max(img.size[0] for img in images)
    ratios = [target_width / img.size[0] for img in images]
    new_heights = [int(img.size[1] * ratio) for img in ratios]
    
    resized_images = [img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                     for img, new_height in zip(images, new_heights)]
    
    # Create new image
    new_height = sum(new_heights)
    merged = Image.new('RGBA', (target_width, new_height), (0, 0, 0, 0))
    
    # Paste images
    y_offset = 0
    for i, img in enumerate(resized_images):
        merged.paste(img, (0, y_offset))
        
        # Add text
        draw = ImageDraw.Draw(merged)
        text_size = int(target_width * 0.05)
        text = f"图片 {i+1}"
        add_text_to_image(draw, text, (20, y_offset + 20), text_size)
        
        y_offset += img.size[1]
    
    return merged

def merge_four_images(images: List[Image.Image]) -> Image.Image:
    """Merge four images in a 2x2 grid."""
    return merge_grid_images(images, 2, 2)

def merge_grid_images(images: List[Image.Image], rows: int, cols: int) -> Image.Image:
    """Merge images in a grid layout."""
    # Calculate target size
    target_width = max(img.size[0] for img in images)
    target_height = max(img.size[1] for img in images)
    
    # Resize all images to the same size
    resized_images = [img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                     for img in images]
    
    # Create new image
    grid_width = target_width * cols
    grid_height = target_height * rows
    merged = Image.new('RGBA', (grid_width, grid_height), (0, 0, 0, 0))
    
    # Paste images
    for i, img in enumerate(resized_images):
        if i >= rows * cols:
            break
            
        row = i // cols
        col = i % cols
        x_offset = col * target_width
        y_offset = row * target_height
        
        merged.paste(img, (x_offset, y_offset))
        
        # Add text
        draw = ImageDraw.Draw(merged)
        text_size = int(min(target_width, target_height) * 0.05)
        text = f"图片 {i+1}"
        add_text_to_image(draw, text, (x_offset + 20, y_offset + 20), text_size)
    
    return merged

def process_images(files: List[Tuple[str, any]]) -> str:
    """Process multiple images and return base64 encoded result."""
    # Sort files by name
    files.sort(key=lambda x: natural_sort_key(x[0]))
    
    # Open images
    images = [Image.open(f[1]) for f in files]
    
    # Merge images
    merged_image = merge_images(images, len(images))
    
    # Convert to RGB for JPEG
    merged_image = merged_image.convert('RGB')
    
    # Save to bytes
    img_bytes = io.BytesIO()
    merged_image.save(img_bytes, format='JPEG', quality=95)
    img_bytes.seek(0)
    
    # Convert to base64
    return base64.b64encode(img_bytes.getvalue()).decode()
