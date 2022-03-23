#!/usr/bin/env python3
import argparse
import jinja2
import os
from enum import Enum
from typing import Dict, Iterator, List, Tuple

from common.basedir import BASEDIR
from selfdrive.car.docs_definitions import Column, RowItem, Star, Tier
from selfdrive.car.car_helpers import interfaces, get_interface_attr
from selfdrive.car.hyundai.radar_interface import RADAR_START_ADDR as HKG_RADAR_START_ADDR
from selfdrive.car.tests.routes import non_tested_cars


def get_all_footnotes():
  all_footnotes = []
  for _, footnotes in get_interface_attr("Footnote").items():
    if footnotes is not None:
      all_footnotes += footnotes
  return {fn: idx + 1 for idx, fn in enumerate(all_footnotes)}


ALL_FOOTNOTES: Dict[Enum, int] = get_all_footnotes()
CARS_MD_OUT = os.path.join(BASEDIR, "docs", "CARS.md")
CARS_MD_TEMPLATE = os.path.join(BASEDIR, "selfdrive", "car", "CARS_template.md")


def get_tier_car_rows() -> List[Tuple[Tier, List[RowItem]]]:
  tier_car_rows: Dict[Tier, list] = {tier: [] for tier in Tier}

  for models in get_interface_attr("CAR_INFO").values():
    for model, car_info in models.items():
      # Hyundai exception: those with radar have openpilot longitudinal
      fingerprint = {0: {}, 1: {HKG_RADAR_START_ADDR: 8}, 2: {}, 3: {}}
      CP = interfaces[model][0].get_params(model, fingerprint=fingerprint, disable_radar=True)

      if CP.dashcamOnly:
        continue

      # A platform can include multiple car models
      if not isinstance(car_info, list):
        car_info = (car_info,)

      for _car_info in car_info:
        stars = _car_info.get_stars(CP, non_tested_cars)
        tier = {5: Tier.GOLD, 4: Tier.SILVER}.get(stars.count(Star.FULL), Tier.BRONZE)
        tier_car_rows[tier].append(_car_info.get_row(ALL_FOOTNOTES, stars))

  # Return tier enum and car rows for each tier
  tiers = []
  for tier, car_rows in tier_car_rows.items():
    tiers.append((tier, sorted(car_rows, key=lambda x: x[0].text + x[1].text)))
  return tiers


def generate_cars_md(tier_car_rows: List[Tuple[Tier, List[RowItem]]], template_fn: str) -> str:
  with open(template_fn, "r") as f:
    template = jinja2.Template(f.read(), trim_blocks=True, lstrip_blocks=True)

  footnotes = [fn.value.text for fn in ALL_FOOTNOTES]
  return template.render(tiers=tier_car_rows, columns=[column.value for column in Column],
                         footnotes=footnotes, Star=Star)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Auto generates supported cars documentation",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument("--template", default=CARS_MD_TEMPLATE, help="Override default template filename")
  parser.add_argument("--out", default=CARS_MD_OUT, help="Override default generated filename")
  args = parser.parse_args()

  with open(args.out, 'w') as f:
    f.write(generate_cars_md(get_tier_car_rows(), args.template))
  print(f"Generated and written to {args.out}")