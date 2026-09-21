#!/usr/bin/env python3
"""Replace the obsolete J3 Ebyte land pattern with the Ai-Thinker Ra-01SH.

This intentionally does not invent antenna/TXEN/RXEN nets.  Those are left
unconnected until the RF path and MCU GPIO allocation are specified.
"""
import argparse
from pathlib import Path
import pcbnew


NET_BY_PAD = {
    1: None,                 # ANT: requires a defined antenna path
    2: "GND",
    3: "3V3",
    4: "SX1262_RESET",
    5: None,                 # TXEN: requires RF-switch/GPIO decision
    6: "SX1262_DIO1",
    7: None,                 # DIO2 unused by current design
    8: None,                 # DIO3 unused by current design
    9: "GND",
    10: "SX1262_BUSY",
    11: None,                # RXEN: requires RF-switch/GPIO decision
    12: "SPI_SCK",
    13: "SPI_MISO",
    14: "SPI_MOSI",
    15: "SX1262_CS",
    16: "GND",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    args = ap.parse_args()

    board = pcbnew.LoadBoard(args.input)
    old = board.FindFootprintByReference("J3")
    if old is None:
        raise SystemExit("J3 not found")

    pos = old.GetPosition()
    orient = old.GetOrientation()
    layer = old.GetLayer()
    ref = old.GetReference()
    value = old.GetValue()

    fp_dir = Path(__file__).with_name("owasso1.pretty")
    new = pcbnew.FootprintLoad(str(fp_dir), "Ra-01SH")
    if new is None:
        raise SystemExit(f"could not load {fp_path}")
    new.SetReference(ref)
    new.SetValue("Ra-01SH-SX1262-915MHz")
    new.SetPosition(pos)
    new.SetOrientation(orient)
    new.SetLayer(layer)

    board.Add(new)
    for pad in new.Pads():
        try:
            number = int(pad.GetNumber())
        except ValueError:
            continue
        net_name = NET_BY_PAD.get(number)
        if net_name is None:
            pad.SetNetCode(0)
        else:
            net = board.FindNet(net_name)
            if net is None:
                raise SystemExit(f"required net missing: {net_name}")
            pad.SetNet(net)
    board.Remove(old)
    pcbnew.SaveBoard(args.output, board)
    print(f"replaced {ref}: {value} -> {new.GetValue()}")
    print(f"preserved position={pos} orientation={orient.AsDegrees()} layer={layer}")
    print("unconnected pads: 1 ANT, 5 TXEN, 7 DIO2, 8 DIO3, 11 RXEN")


if __name__ == "__main__":
    main()
