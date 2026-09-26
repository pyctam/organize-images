# Image Trimmer

`trim_image.py` is a Python command-line utility that automatically removes solid or near-solid background space around an image's content.

It scans the image pixel-by-pixel, identifies pixels that are different from the specified background color, determines the smallest bounding box containing those pixels, adds an optional outward offset, and saves the cropped image using the original filename with `-trimmed` appended.

For example:

```text
back.png
```

becomes:

```text
back-trimmed.png
```

## Requirements

- Python 3
- Pillow

Install Pillow with:

```bash
pip install Pillow
```

If you are using a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install Pillow
```

## Usage

```bash
python trim_image.py IMAGE BACKGROUND OFFSET [TOLERANCE]
```

### Parameters

| Parameter | Required | Description |
|---|---|---|
| `IMAGE` | Yes | Path to the image to process |
| `BACKGROUND` | Yes | Background RGB color in `R,G,B` format |
| `OFFSET` | Yes | Number of pixels to preserve around the detected content |
| `TOLERANCE` | No | Allowed difference from the background RGB color. Defaults to `0` |

Both `OFFSET` and `TOLERANCE` must be greater than or equal to `0`.

### IMAGE

The path to the input image.

Examples:

```bash
"back.png"
```

or:

```bash
"/path/to/images/back.png"
```

The output is saved in the same directory as the input image.

### BACKGROUND

The RGB color that should be considered the image background.

For example:

```text
254,254,254
```

represents:

```text
#FEFEFE
```

Other examples:

```text
255,255,255  # White
0,0,0        # Black
255,0,0      # Red
```

Do not include the `#` when specifying the color.

### OFFSET

The number of pixels to keep around the detected content.

For example:

```bash
5
```

means that after the content boundary is detected, the crop is expanded outward by up to 5 pixels on every side.

An offset of:

```bash
0
```

means that the image is cropped exactly to the detected content boundary.

The offset is automatically limited by the image boundaries.

### TOLERANCE

The tolerance controls how closely a pixel must match the supplied background color to be considered background.

For example, with:

```text
Background: (254, 254, 254)
Tolerance: 5
```

a pixel is considered background when each individual RGB channel is within 5 of the corresponding background channel.

For example:

```text
(254, 254, 254)  -> background
(250, 250, 250)  -> background
(255, 255, 255)  -> background
(249, 254, 253)  -> background
```

while:

```text
(248, 254, 254)  -> not background
```

because the red channel differs by 6.

A tolerance of `0` means an exact RGB match is required.

## RGB and RGBA Images

The script supports both RGB and RGBA images.

For RGB images, pixels are evaluated using their RGB values.

For RGBA images:

- Fully transparent pixels (`alpha = 0`) are always treated as background.
- Visible pixels are evaluated using their RGB values.
- The original alpha channel is preserved when the cropped image is saved.

## How It Works

The script:

1. Opens the input image.
2. Determines its dimensions and color mode.
3. Scans every pixel.
4. Compares each pixel with the supplied background color and tolerance.
5. Determines the first and last non-background pixels in both dimensions.
6. Creates a bounding box around the detected content.
7. Expands that bounding box by the requested offset.
8. Ensures the crop does not extend outside the original image.
9. Crops the original image.
10. Saves the result with `-trimmed` added to the filename.

## Example

Command:

```bash
python trim_image.py "back.png" "254,254,254" 5 5
```

Output:

```text
============================================================
IMAGE TRIM
============================================================
Input file: back.png
Original image size: 1448 x 1086
Image mode: RGB

Scanning image: 1448 x 1086
Background RGB: (254, 254, 254)
Background tolerance: 5
Alpha channel: no
Total pixels: 1,572,528
Background pixels: 494,291
Non-background pixels: 1,078,237
Detected content bounding box: (17, 24, 1431, 1045)
Detected content size: 1414 x 1021

Requested offset: 5px
Final crop box: (12, 19, 1436, 1050)
Final image size: 1424 x 1031
Pixels removed: left=12, top=19, right=12, bottom=36

Saved: back-trimmed.png
============================================================
```

In this example:

- Original size: `1448 x 1086`
- Detected content starts at `(17, 24)`
- Detected content ends at `(1431, 1045)`
- A `5px` offset is added around the content
- Final crop is `(12, 19, 1436, 1050)`
- Final image size: `1424 x 1031`
- Output: `back-trimmed.png`

## More Examples

### Exact white background

```bash
python trim_image.py "image.png" "255,255,255" 10
```

Since tolerance isn't specified, it defaults to `0`.

### Near-white background

```bash
python trim_image.py "image.png" "254,254,254" 5 5
```

This uses a 5-pixel offset and a tolerance of 5.

### No additional padding

```bash
python trim_image.py "image.png" "254,254,254" 0 5
```

The content is cropped to its detected boundary without adding additional padding.

### Exact color matching with no padding

```bash
python trim_image.py "image.png" "254,254,254" 0
```

This uses exact RGB matching and no offset.

## Output Filename

The original file is never overwritten.

The script adds `-trimmed` before the file extension:

```text
image.png       -> image-trimmed.png
image.jpg       -> image-trimmed.jpg
photo.jpeg      -> photo-trimmed.jpeg
drawing.webp    -> drawing-trimmed.webp
```

The output is saved in the same directory as the input image.

## Notes

### Choosing the Tolerance

If the background is a perfectly uniform color, use:

```text
tolerance = 0
```

If the background contains slight color variations, use a small tolerance:

```text
tolerance = 2
```

or:

```text
tolerance = 5
```

A higher tolerance causes more colors to be classified as background, which can cause faint edges or low-contrast content to be excluded. For that reason, the tolerance should generally be kept as low as practical.

### Choosing the Offset

The offset is independent of the tolerance.

For example:

```bash
python trim_image.py "image.png" "254,254,254" 10 3
```

means:

```text
Background color     = 254,254,254
Background tolerance = 3
Content padding      = 10px
```

The tolerance determines **what counts as background**.

The offset determines **how much background is retained around the detected content**.
