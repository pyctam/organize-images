#!/usr/bin/env python3

import argparse
import os
import sys

from PIL import Image


def parse_rgb(value):
    """Parse RGB color in the form R,G,B."""

    try:
        parts = value.split(",")

        if len(parts) != 3:
            raise ValueError

        rgb = tuple(int(x.strip()) for x in parts)

        if any(x < 0 or x > 255 for x in rgb):
            raise ValueError

        return rgb

    except ValueError:
        raise argparse.ArgumentTypeError(
            "RGB must be in the format R,G,B "
            "with values between 0 and 255."
        )


def is_background(pixel, background_rgb, tolerance, has_alpha):
    """
    Determine whether a pixel should be considered background.

    For RGBA images:
        Alpha == 0 -> always background.

    For all other pixels:
        RGB channels are compared against the supplied background
        using the specified tolerance.
    """

    # RGBA / alpha-aware image
    if has_alpha:
        r, g, b, a = pixel

        # Fully transparent pixels are always background.
        if a == 0:
            return True

    else:
        r, g, b = pixel

    br, bg, bb = background_rgb

    return (
        abs(r - br) <= tolerance
        and
        abs(g - bg) <= tolerance
        and
        abs(b - bb) <= tolerance
    )


def find_content_bbox(image, background_rgb, tolerance):
    """
    Find the bounding box of all pixels that are NOT background.

    Returns:
        (left, top, right, bottom)

    right and bottom are exclusive, matching Pillow's crop()
    convention.

    Returns None if the entire image is background.
    """

    width, height = image.size

    # Determine whether the image has an alpha channel.
    has_alpha = "A" in image.getbands()

    # Convert to RGBA if alpha exists, otherwise RGB.
    if has_alpha:
        scan_image = image.convert("RGBA")
    else:
        scan_image = image.convert("RGB")

    pixels = scan_image.load()

    print(f"Scanning image: {width} x {height}")
    print(f"Background RGB: {background_rgb}")
    print(f"Background tolerance: {tolerance}")
    print(f"Alpha channel: {'yes' if has_alpha else 'no'}")

    left = width
    top = height
    right = -1
    bottom = -1

    non_background_count = 0
    background_count = 0

    for y in range(height):
        for x in range(width):

            pixel = pixels[x, y]

            if is_background(
                pixel,
                background_rgb,
                tolerance,
                has_alpha
            ):
                background_count += 1

            else:
                non_background_count += 1

                if x < left:
                    left = x

                if y < top:
                    top = y

                if x > right:
                    right = x

                if y > bottom:
                    bottom = y

    total_pixels = width * height

    print(f"Total pixels: {total_pixels:,}")
    print(f"Background pixels: {background_count:,}")
    print(f"Non-background pixels: {non_background_count:,}")

    if non_background_count == 0:
        return None

    # Convert max pixel coordinates to exclusive crop coordinates.
    bbox = (
        left,
        top,
        right + 1,
        bottom + 1
    )

    content_width = bbox[2] - bbox[0]
    content_height = bbox[3] - bbox[1]

    print(f"Detected content bounding box: {bbox}")
    print(
        f"Detected content size: "
        f"{content_width} x {content_height}"
    )

    return bbox


def expand_bbox(bbox, image_size, offset):
    """
    Expand bounding box by offset pixels.

    The result is clamped so it never goes outside the image.
    """

    left, top, right, bottom = bbox
    width, height = image_size

    return (
        max(0, left - offset),
        max(0, top - offset),
        min(width, right + offset),
        min(height, bottom + offset)
    )


def make_output_path(input_path):
    """
    Add '-trimmed' before the file extension.

    Example:
        image.png -> image-trimmed.png
        image.jpg -> image-trimmed.jpg
    """

    directory = os.path.dirname(input_path)
    filename = os.path.basename(input_path)

    name, extension = os.path.splitext(filename)

    return os.path.join(
        directory,
        f"{name}-trimmed{extension}"
    )


def trim_image(
    input_path,
    background_rgb,
    offset,
    tolerance
):
    """Load, analyze, crop and save the image."""

    if offset < 0:
        raise ValueError(
            "Offset must be greater than or equal to zero."
        )

    if tolerance < 0:
        raise ValueError(
            "Tolerance must be greater than or equal to zero."
        )

    if not os.path.isfile(input_path):
        raise FileNotFoundError(
            f"File not found: {input_path}"
        )

    print()
    print("=" * 60)
    print("IMAGE TRIM")
    print("=" * 60)

    print(f"Input file: {input_path}")

    with Image.open(input_path) as image:

        original_width, original_height = image.size

        print(
            f"Original image size: "
            f"{original_width} x {original_height}"
        )

        print(f"Image mode: {image.mode}")
        print()

        # ---------------------------------------------------------
        # Find non-background content.
        # ---------------------------------------------------------

        bbox = find_content_bbox(
            image,
            background_rgb,
            tolerance
        )

        if bbox is None:
            raise ValueError(
                "No non-background pixels were found. "
                "The entire image appears to be background."
            )

        # ---------------------------------------------------------
        # Add requested outward offset.
        # ---------------------------------------------------------

        print()
        print(f"Requested offset: {offset}px")

        crop_box = expand_bbox(
            bbox,
            image.size,
            offset
        )

        print(f"Final crop box: {crop_box}")

        crop_left, crop_top, crop_right, crop_bottom = crop_box

        final_width = crop_right - crop_left
        final_height = crop_bottom - crop_top

        print(
            f"Final image size: "
            f"{final_width} x {final_height}"
        )

        # ---------------------------------------------------------
        # Calculate how much was removed from each side.
        # ---------------------------------------------------------

        removed_left = crop_left
        removed_top = crop_top
        removed_right = original_width - crop_right
        removed_bottom = original_height - crop_bottom

        print(
            f"Pixels removed: "
            f"left={removed_left}, "
            f"top={removed_top}, "
            f"right={removed_right}, "
            f"bottom={removed_bottom}"
        )

        # ---------------------------------------------------------
        # Crop using the original image.
        #
        # This preserves the original mode, including alpha.
        # ---------------------------------------------------------

        cropped = image.crop(crop_box)

        output = make_output_path(input_path)

        # ---------------------------------------------------------
        # Save.
        # ---------------------------------------------------------

        cropped.save(output)

    print()
    print(f"Saved: {output}")
    print("=" * 60)

    return output


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Trim background from an image based on an RGB color "
            "with configurable color tolerance."
        )
    )

    parser.add_argument(
        "image",
        help="Path to the input image."
    )

    parser.add_argument(
        "background",
        type=parse_rgb,
        help=(
            "Background RGB color, "
            "for example: 254,254,254"
        )
    )

    parser.add_argument(
        "offset",
        type=int,
        help=(
            "Number of pixels to preserve around the detected "
            "content. Must be >= 0."
        )
    )

    parser.add_argument(
        "tolerance",
        type=int,
        nargs="?",
        default=0,
        help=(
            "Background color tolerance. "
            "0 means exact RGB matching. "
            "Default: 0."
        )
    )

    args = parser.parse_args()

    if args.offset < 0:
        parser.error(
            "Offset must be greater than or equal to zero."
        )

    if args.tolerance < 0:
        parser.error(
            "Tolerance must be greater than or equal to zero."
        )

    try:

        trim_image(
            input_path=args.image,
            background_rgb=args.background,
            offset=args.offset,
            tolerance=args.tolerance
        )

    except Exception as e:

        print()
        print(f"ERROR: {e}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
    
