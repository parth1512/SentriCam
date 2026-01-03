import argparse
import shutil
from pathlib import Path
from typing import List, Tuple

from utils import set_seed, yolo_image_extensions, ensure_dir, copy_file


def collect_pairs(root: Path) -> List[Tuple[Path, Path]]:
	pairs: List[Tuple[Path, Path]] = []
	for split in ["train", "valid", "val", "test"]:
		img_dir = root / split / "images"
		lbl_dir = root / split / "labels"
		if not img_dir.exists() or not lbl_dir.exists():
			continue
		for img_path in img_dir.rglob("*"):
			if img_path.suffix.lower() in yolo_image_extensions():
				label_path = lbl_dir / (img_path.stem + ".txt")
				if label_path.exists():
					pairs.append((img_path, label_path))
	return pairs


def write_data_yaml(target_root: Path) -> None:
	data_yaml = f"""
path: {target_root}
train: images/train
val: images/val
test: images/test

names:
  0: license_plate
""".strip()
	with open(target_root / "data.yaml", "w", encoding="utf-8") as f:
		f.write(data_yaml + "\n")


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("--source-root", type=str, required=True, help="Path to existing dataset root containing train/valid/test")
	parser.add_argument("--target-root", type=str, default=str(Path(__file__).resolve().parents[1] / "data"))
	parser.add_argument("--seed", type=int, default=42)
	args = parser.parse_args()

	set_seed(args.seed)
	source_root = Path(args.source_root)
	target_root = Path(args.target_root)

	pairs = collect_pairs(source_root)
	if not pairs:
		raise RuntimeError("No (image,label) pairs found in source-root. Ensure YOLO folder structure under train/val/test.")

	# Shuffle and split 70/20/10
	n = len(pairs)
	indices = list(range(n))
	import random
	random.shuffle(indices)
	train_end = int(0.7 * n)
	val_end = int(0.9 * n)

	train_idx = indices[:train_end]
	val_idx = indices[train_end:val_end]
	test_idx = indices[val_end:]

	# Prepare dirs
	for split in ["train", "val", "test"]:
		ensure_dir(target_root / "images" / split)
		ensure_dir(target_root / "labels" / split)

	def export(split: str, subset_idx: List[int]) -> None:
		for i in subset_idx:
			img_path, lbl_path = pairs[i]
			copy_file(img_path, target_root / "images" / split / img_path.name)
			copy_file(lbl_path, target_root / "labels" / split / lbl_path.name)

	export("train", train_idx)
	export("val", val_idx)
	export("test", test_idx)

	write_data_yaml(target_root)

	print(f"Total pairs: {n}")
	print(f"Train: {len(train_idx)} | Val: {len(val_idx)} | Test: {len(test_idx)}")
	print(f"data.yaml written to: {target_root / 'data.yaml'}")


if __name__ == "__main__":
	main()







