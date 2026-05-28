# Spurgeon Scene Notes

## Setting
**The Metropolitan Tabernacle**, Newington, London — built 1861, seats ~5,500.
Spurgeon preached here from 1861 until his death in 1892. The interior features
a grand Greek Revival / Gothic hybrid architecture: stone columns, arched galleries,
a central elevated pulpit, and gas lighting.

## Art Style
**Victorian woodcut / engraving** — flat vector illustration with bold outlines,
limited hatching for shadow, and no photorealism. References: 19th century
illustrated newspapers (The Illustrated London News), Gustave Doré Bible
engravings, Victorian book frontispieces.

## Color Palette
| Role | Hex | Description |
|------|-----|-------------|
| Background sky/ceiling | `#2a1a0a` | Deep espresso dark |
| Stone walls | `#7a5c38` | Warm sandstone |
| Wooden pews | `#8b5e3c` | Rich mahogany |
| Pulpit | `#a06a30` | Polished oak |
| Gaslight glow | `#ffd27f` | Warm gold |
| Flesh tones | `#c4956a` | Victorian portrait skin |
| Coat/dark clothing | `#1a0f05` → `#0a0504` | Near-black brown |
| White linen/paper | `#e8d5a8` | Aged cream/parchment |
| Caption text | `#f5e6c8` | Warm white |
| Caption background | `#1a0f05` at 70% opacity | Dark semi-transparent |

## Spurgeon's Appearance (1861–1875 era)
- Age approximately 27–40 in this rendering
- **Stout, round-faced**, notably broad-shouldered
- **Dark full moustache** — his most distinctive feature in this period
- **Heavy dark sideburns** reaching to jaw
- Dark hair, side-parted, medium length
- **Victorian frock coat** — full black coat with long skirts
- **White collar and cravat** — always immaculate
- **Open Bible** on the pulpit in front of him

## Spurgeon's Preaching Style
- Famous for **theatrical delivery** — wide gestures, voice modulation
- Would lower to a near-whisper, then suddenly boom to fill 6,000 seats
- Leaned forward and gripped the pulpit on intense passages
- Raised right hand/arm on declaratory moments ("God declares...")
- Stood very upright between emphatic passages

## Animation Notes

### Idle State
- **Body sway**: ±2° rotation on a 3.2-second loop, easing in/out
- **Head nod**: very slight, ±3px y-movement on 2.5s loop (offset from body)
- **Congregation**: gentle group sway, all 12 figures offset by 0.2s each

### Sentence Boundary Events
- **Body lean**: translate Y +8px, duration 0.3s ease-in, return 0.5s ease-out
- **Grip on pulpit**: left arm group slight downward press

### Intensity Peak Events (RMS threshold)
- **Right arm raise**: arm-right rotates from 0° to -35° (upward), duration 0.4s
- **Return**: 0.8s ease-out return to 0°
- **Head emphasis**: ±5px forward (Z-suggestion via slight scale)

## Congregation
12 figures, 3 rows of pews:
- **Row 1 (back)**: Figures 1–6 — seated, partially visible above pew backs
- **Row 2 (middle)**: Figures 7–9 — seated, mixed gender/age
- **Row 3 (front)**: Figures 10–12 — clearly visible, more detail

Congregation sway: all figures share a base sway of ±1.5° on a 4-second loop,
with each figure offset by `index * 0.18` seconds to create a crowd wave effect.

## Caption Zone
- **Position**: upper-left quadrant, x:40 y:95 w:820 h:350
- **Above the congregation**, clear of heads in rows 1–3
- **Font**: serif typeface (e.g. Playfair Display or Lora) for period feel
- **Size**: 52px for normal phrases, 64px for short emphatic phrases (≤4 words)
- **Color**: `#f5e6c8` text on semi-transparent dark background pill
- **Animation**: fade-in 0.3s → hold → fade-out 0.3s

## Future Per-Author Variants
Each author will have their own `scene_notes.md` defining:
- Setting name and era
- Color palette delta (inherit base or override)
- Character appearance notes
- Preaching style motion cues
- Caption zone position (may differ per layout)
