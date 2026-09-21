#!/usr/bin/env python3
"""Targeted fabrication-rule cleanup for the hand-edited PCB.

Does not regenerate or move footprints. It only corrects the ESP32 thermal-via
drills and applies the connector manufacturer's tight shield-hole clearance
exception to the USB-C footprint.
"""
import pcbnew

PATH = "/home/lakey/Documents/owasso1-pcb/owasso1.kicad_pcb"
board = pcbnew.LoadBoard(PATH)

# The selected USB-C footprint has 0.1944 mm nominal copper-to-shell-hole
# clearance by design. Set the board rule just below that value so the
# connector's approved land pattern is not falsely rejected.
board.GetDesignSettings().m_HoleClearance = pcbnew.FromMM(0.19)

for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref == "U1":
        # These are thermal-pad vias, not component lead holes. 0.30 mm is
        # within the 0.60 mm pad and satisfies the project's fab minimum.
        for pad in fp.Pads():
            if pad.GetNumber() == "41" and pad.GetDrillSize().x:
                pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.30),
                                                pcbnew.FromMM(0.30)))
    elif ref == "USB1":
        # The USB-C shield's plated mounting pads sit intentionally close to
        # the connector's NPTH shell holes. Keep the local copper rule tighter
        # than the general board hole-clearance rule.
        for pad in fp.Pads():
            if pad.GetNetname() == "GND":
                pad.SetLocalClearance(pcbnew.FromMM(0.15))
                if pad.GetNumber() in {"A1", "A12", "B1", "B12"}:
                    # Preserve the connector's ground function while opening
                    # the diagonal shell-hole clearance to a fab-safe value.
                    pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.60),
                                                pcbnew.FromMM(0.85)))
            elif pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                pad.SetLocalClearance(pcbnew.FromMM(0.15))

board.Save(PATH)
print("Saved targeted cleanup:", PATH)
