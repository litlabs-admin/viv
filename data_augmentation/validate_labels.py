"""validate_labels.py
Scan a dataset folder (images + YOLO .txt labels) and report:
- missing image/label pairs
- empty label files
- malformed label lines
- coordinates outside [0,1]
- class indices outside range of classes.txt

Usage:
python .\validate_labels.py --src raw --classes raw\classes.txt
"""
import argparse
import os
import glob
import sys

IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']


def find_image_for_base(src, base):
    for ext in IMAGE_EXTS:
        p = os.path.join(src, base + ext)
        if os.path.exists(p):
            return p
    # case-insensitive search
    for p in glob.glob(os.path.join(src, base + '.*')):
        if os.path.splitext(p)[1].lower() in IMAGE_EXTS:
            return p
    return None


def read_classes(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [l.strip() for l in f.read().splitlines() if l.strip()]


def is_float(x):
    try:
        float(x)
        return True
    except:
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--src', required=True, help='Source folder containing images and .txt labels')
    p.add_argument('--classes', required=False, help='Path to classes.txt')
    args = p.parse_args()

    src = args.src
    classes = read_classes(args.classes) if args.classes else []

    txt_files = sorted([os.path.basename(x) for x in glob.glob(os.path.join(src, '*.txt')) if os.path.basename(x).lower() != (os.path.basename(args.classes) if args.classes else '').lower()])
    img_files = []
    for ext in IMAGE_EXTS:
        img_files.extend([os.path.basename(x) for x in glob.glob(os.path.join(src, '*' + ext))])
    img_files = sorted(img_files)

    # map basenames
    txt_bases = [os.path.splitext(x)[0] for x in txt_files]
    img_bases = [os.path.splitext(x)[0] for x in img_files]

    missing_label = [b for b in img_bases if b not in txt_bases]
    missing_image = [b for b in txt_bases if b not in img_bases]

    empty_labels = []
    malformed = {}
    out_of_range = {}
    bad_class_idx = {}

    for txt in txt_files:
        txt_path = os.path.join(src, txt)
        base = os.path.splitext(txt)[0]
        try:
            lines = [l for l in open(txt_path, 'r', encoding='utf-8').read().splitlines()]
        except Exception as e:
            malformed[txt] = [f'Failed to read file: {e}']
            continue
        # count non-empty
        non_empty = [l.strip() for l in lines if l.strip()]
        if len(non_empty) == 0:
            empty_labels.append(txt)
            continue
        for i, line in enumerate(non_empty, start=1):
            parts = line.strip().split()
            if len(parts) != 5:
                malformed.setdefault(txt, []).append(f'Line {i}: expected 5 values, got {len(parts)} -> "{line}"')
                continue
            cls = parts[0]
            coords = parts[1:]
            if not cls.isdigit():
                malformed.setdefault(txt, []).append(f'Line {i}: class id not integer -> "{cls}"')
            else:
                cls_i = int(cls)
                if classes and (cls_i < 0 or cls_i >= len(classes)):
                    bad_class_idx.setdefault(txt, []).append(f'Line {i}: class {cls_i} out of range [0,{len(classes)-1}]')
            # check floats
            if not all(is_float(x) for x in coords):
                malformed.setdefault(txt, []).append(f'Line {i}: coords not all floats -> "{line}"')
                continue
            nums = [float(x) for x in coords]
            x_c, y_c, w, h = nums
            problems = []
            if not (0.0 <= x_c <= 1.0):
                problems.append(f'x_center={x_c}')
            if not (0.0 <= y_c <= 1.0):
                problems.append(f'y_center={y_c}')
            if not (0.0 < w <= 1.0):
                problems.append(f'width={w}')
            if not (0.0 < h <= 1.0):
                problems.append(f'height={h}')
            if problems:
                out_of_range.setdefault(txt, []).append(f'Line {i}: ' + ', '.join(problems) + f' -> "{line}"')

    # Print report
    print('=== Validation report ===')
    print(f'Source folder: {src}')
    print(f'Classes file: {args.classes if args.classes else "(none)"} (loaded {len(classes)} classes)')
    print('')
    print(f'Total images found: {len(img_files)}')
    print(f'Total .txt label files found: {len(txt_files)}')
    print('')

    if missing_label:
        print(f'Images without matching .txt labels ({len(missing_label)}):')
        for b in missing_label:
            print('  -', b)
    else:
        print('All images have matching .txt label files.')
    print('')

    if missing_image:
        print(f'.txt files without matching images ({len(missing_image)}):')
        for b in missing_image:
            print('  -', b)
    else:
        print('All .txt label files have matching images.')
    print('')

    print(f'Empty label files: {len(empty_labels)}')
    for t in empty_labels[:50]:
        print('  -', t)
    print('')

    total_malformed = sum(len(v) for v in malformed.values())
    if total_malformed:
        print(f'Malformed label lines: {total_malformed} (in {len(malformed)} files)')
        for k, v in malformed.items():
            print('File:', k)
            for item in v[:10]:
                print('  ', item)
    else:
        print('No malformed label lines detected.')
    print('')

    total_out_of_range = sum(len(v) for v in out_of_range.values())
    if total_out_of_range:
        print(f'Coordinates out of range or invalid sizes: {total_out_of_range} (in {len(out_of_range)} files)')
        for k, v in out_of_range.items():
            print('File:', k)
            for item in v[:10]:
                print('  ', item)
    else:
        print('All coordinates are within expected ranges [0,1] and widths/heights > 0.')
    print('')

    if bad_class_idx:
        print('Invalid class indices found:')
        for k, v in bad_class_idx.items():
            print('File:', k)
            for item in v:
                print('  ', item)
    else:
        if classes:
            print('All class indices are within the classes range.')
        else:
            print('No classes.txt provided; skipped class index range checks.')

    print('\n=== End of report ===')

    # exit code 0 even if issues found (we're just reporting)

if __name__ == '__main__':
    main()
