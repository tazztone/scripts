#!/usr/bin/env python3
"""
Annotate Toppreise screenshot (wide 1024x954) focusing strictly on visible features:
1. Unified Power Filter Bar
2. Dynamic Deal Discount Heatmap
3. 1-Click Category Quick-Block & Smart Taxonomy
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter

def draw_vector_icon(draw, icon_type, x, y, size, color):
    """Draw crisp procedural icons."""
    if icon_type == "bolt": # Lightning bolt / Filter
        pts = [
            (x + size*0.55, y),
            (x + size*0.15, y + size*0.55),
            (x + size*0.45, y + size*0.55),
            (x + size*0.35, y + size),
            (x + size*0.85, y + size*0.4),
            (x + size*0.55, y + size*0.4),
        ]
        draw.polygon(pts, fill=color)
    elif icon_type == "flame": # Flame / Heatmap
        pts = [
            (x + size*0.5, y),
            (x + size*0.75, y + size*0.35),
            (x + size*0.85, y + size*0.7),
            (x + size*0.65, y + size*0.95),
            (x + size*0.35, y + size*0.95),
            (x + size*0.15, y + size*0.7),
            (x + size*0.3, y + size*0.45),
            (x + size*0.45, y + size*0.55),
        ]
        draw.polygon(pts, fill=color)
        inner = [
            (x + size*0.5, y + size*0.45),
            (x + size*0.65, y + size*0.7),
            (x + size*0.5, y + size*0.9),
            (x + size*0.35, y + size*0.7),
        ]
        draw.polygon(inner, fill=(255, 255, 255, 220))
    elif icon_type == "ban": # Ban / Category Block
        draw.ellipse([x, y, x + size, y + size], outline=color, width=max(2, int(size*0.14)))
        offset = size * 0.2
        draw.line([x + offset, y + offset, x + size - offset, y + size - offset], fill=color, width=max(2, int(size*0.14)))

def create_annotated_screenshot(src_path, output_png, output_webp):
    orig = Image.open(src_path).convert("RGBA")
    orig_w, orig_h = orig.size  # 1024 x 954

    # Canvas dimensions
    canvas_w = 1560
    canvas_h = 1060
    
    # Base dark background
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (10, 14, 23, 255))
    
    # Ambient glows
    glow_overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_overlay)
    
    for r in range(480, 0, -15):
        alpha = int(22 * (1 - r / 480))
        glow_draw.ellipse([1200 - r, 200 - r, 1200 + r, 200 + r], fill=(6, 182, 212, alpha))
    for r in range(480, 0, -15):
        alpha = int(24 * (1 - r / 480))
        glow_draw.ellipse([1220 - r, 510 - r, 1220 + r, 510 + r], fill=(245, 158, 11, alpha))
    for r in range(480, 0, -15):
        alpha = int(24 * (1 - r / 480))
        glow_draw.ellipse([1200 - r, 820 - r, 1200 + r, 820 + r], fill=(244, 63, 94, alpha))

    canvas = Image.alpha_composite(canvas, glow_overlay)
    draw = ImageDraw.Draw(canvas)

    # Fonts
    font_bold = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
    font_med = "/usr/share/fonts/truetype/ubuntu/Ubuntu-M.ttf"
    font_reg = "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"

    header_font = ImageFont.truetype(font_bold, 22)
    sub_font = ImageFont.truetype(font_med, 14)
    title_font = ImageFont.truetype(font_bold, 17)
    body_font = ImageFont.truetype(font_reg, 14)
    badge_font = ImageFont.truetype(font_bold, 11)

    # Top header
    draw.text((40, 20), "TOPPREISE.CH POWER SUITE", font=header_font, fill=(255, 255, 255, 255))
    draw.text((380, 27), "Deal Feed Filtering & Dynamic Heatmap on neue-toppreise", font=sub_font, fill=(148, 163, 184, 255))

    pill_text = "neue-toppreise"
    pill_w = badge_font.getlength(pill_text) + 22
    draw.rounded_rectangle([canvas_w - 40 - pill_w, 20, canvas_w - 40, 44], radius=12, fill=(30, 41, 59, 255), outline=(51, 65, 85, 255), width=1)
    draw.text((canvas_w - 29 - pill_w, 25), pill_text, font=badge_font, fill=(56, 189, 248, 255))

    # Screenshot placement
    sc_x = 40
    sc_y = 60
    
    # Drop shadow for screenshot
    shadow_blur = 24
    shadow = Image.new("RGBA", (orig_w + shadow_blur * 2, orig_h + shadow_blur * 2), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle(
        [shadow_blur, shadow_blur, shadow_blur + orig_w, shadow_blur + orig_h],
        radius=14,
        fill=(0, 0, 0, 220)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur // 2))
    canvas.paste(shadow, (sc_x - shadow_blur + 4, sc_y - shadow_blur + 10), shadow)

    # Rounded screenshot mask
    mask = Image.new("L", (orig_w, orig_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, orig_w, orig_h], radius=14, fill=255)
    
    border_img = Image.new("RGBA", (orig_w, orig_h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(border_img)
    b_draw.rounded_rectangle([0, 0, orig_w - 1, orig_h - 1], radius=14, outline=(75, 85, 99, 180), width=2)
    
    canvas.paste(orig, (sc_x, sc_y), mask)
    canvas.paste(border_img, (sc_x, sc_y), border_img)

    # Callout renderer with clean orthogonal elbows
    def draw_callout_box(x, y, w, h, icon_name, tag, tag_color, title, lines, pointer_target, line_color):
        px, py = pointer_target
        
        card_mid_y = y + h // 2
        start_pt = (x, card_mid_y)
        elbow_x = x - 30
        
        # Glowing connection line
        glow_line = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        g_ldraw = ImageDraw.Draw(glow_line)
        g_ldraw.line([start_pt, (elbow_x, card_mid_y), (elbow_x, py), (px, py)], fill=(*line_color[:3], 90), width=6)
        g_ldraw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=(*line_color[:3], 120))
        glow_line = glow_line.filter(ImageFilter.GaussianBlur(3))
        canvas.paste(Image.alpha_composite(canvas.crop((0, 0, canvas_w, canvas_h)), glow_line))
        
        # Solid connection line
        draw.line([start_pt, (elbow_x, card_mid_y), (elbow_x, py), (px, py)], fill=line_color, width=2)
        
        # Target marker
        draw.ellipse([px - 5, py - 5, px + 5, py + 5], fill=line_color)
        draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 255, 255, 255))
        draw.ellipse([px - 14, py - 14, px + 14, py + 14], outline=(*line_color[:3], 200), width=2)

        # Card shadow
        c_shadow = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0))
        cs_draw = ImageDraw.Draw(c_shadow)
        cs_draw.rounded_rectangle([12, 12, w + 12, h + 12], radius=14, fill=(0, 0, 0, 190))
        c_shadow = c_shadow.filter(ImageFilter.GaussianBlur(8))
        canvas.paste(c_shadow, (x - 12, y - 8), c_shadow)

        # Card container
        card_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_img)
        card_draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=12, fill=(17, 24, 39, 248), outline=(*line_color[:3], 210), width=2)

        # Draw icon
        draw_vector_icon(card_draw, icon_name, 18, 15, 18, tag_color)

        # Tag pill
        tag_w = badge_font.getlength(tag) + 16
        card_draw.rounded_rectangle([42, 14, 42 + tag_w, 33], radius=6, fill=(*tag_color[:3], 45), outline=(*tag_color[:3], 180), width=1)
        card_draw.text((50, 17), tag, font=badge_font, fill=tag_color)

        # Card Title
        card_draw.text((18, 44), title, font=title_font, fill=(255, 255, 255, 255))

        # Bullet list items
        curr_y = 78
        for line in lines:
            card_draw.ellipse([18, curr_y + 5, 23, curr_y + 10], fill=line_color)
            card_draw.text((32, curr_y), line, font=body_font, fill=(203, 213, 225, 255))
            curr_y += 24

        canvas.paste(card_img, (x, y), card_img)

    # 1. Unified Filter Toolbar (Target: Reset & Toolbar controls at sc_x + 648, sc_y + 318)
    draw_callout_box(
        x=1110, y=80, w=410, h=240,
        icon_name="bolt",
        tag="POWER TOOLBAR",
        tag_color=(6, 182, 212, 255),
        title="Unified Power Filter Bar",
        lines=[
            "Negativ-Filter: Exclude unwanted keywords",
            "Min-Offers Stepper: Filter by merchant count",
            "Live Counters: Preview hidden items & blocked tags",
            "Heatmap Toggle: 1-Click dynamic thermal coloring",
            "Reset: Restore default feed view instantly"
        ],
        pointer_target=(sc_x + 648, sc_y + 318),
        line_color=(6, 182, 212, 255)
    )

    # 2. Rabatt-Heatmap (Target: -39% discount badge & glowing amber background at sc_x + 330, sc_y + 560)
    draw_callout_box(
        x=1110, y=380, w=410, h=240,
        icon_name="flame",
        tag="THERMAL SHADING",
        tag_color=(245, 158, 11, 255),
        title="Dynamic Deal Discount Heatmap",
        lines=[
            "Automatic thermal background gradients on deal cards",
            "Calibrated by discount magnitude (% Differenz):",
            "  - 0-15%: Midnight Blue (Cold deals)",
            "  - 35%: Warm Amber (Strong discounts)",
            "  - 70%+: Volcanic Ruby Red (Massive savings)"
        ],
        pointer_target=(sc_x + 330, sc_y + 560),
        line_color=(245, 158, 11, 255)
    )

    # 3. 1-Click Inline Category Quick-Block & Tooltip (Target: Pink 'Eau De Parfum' pill button at sc_x + 95, sc_y + 655)
    draw_callout_box(
        x=1110, y=680, w=410, h=250,
        icon_name="ban",
        tag="CATEGORY BLOCKING",
        tag_color=(244, 63, 94, 255),
        title="1-Click Category Quick-Block",
        lines=[
            "Direct inline category quick-block button on cards",
            "Instantly hides matching items across the feed",
            "Smart taxonomy resolver: 'Eau De Parfum' -> 'Drogerie'",
            "Hover preview tooltip confirms root category",
            "Non-blocking glassmorphic Toast Undo notification"
        ],
        pointer_target=(sc_x + 95, sc_y + 655),
        line_color=(244, 63, 94, 255)
    )

    # Save output
    canvas.save(output_png, "PNG", optimize=True)
    canvas.save(output_webp, "WEBP", quality=92, method=6)
    print(f"Successfully generated wide screenshot infographic:\n- {output_png}\n- {output_webp}")

if __name__ == "__main__":
    src = "/home/tazztone/.gemini/antigravity-ide/brain/d8407f79-485a-4ba0-bf03-ae441b553729/.user_uploaded/media_1787743263048.png"
    out_png = "/home/tazztone/_coding/scripts/userscripts/toppreise/Screenshot.png"
    out_webp = "/home/tazztone/_coding/scripts/userscripts/toppreise/Screenshot.webp"
    create_annotated_screenshot(src, out_png, out_webp)
