# RX3 Texture Editor Android v0.1

3 screen flow:
OPEN -> RX3 list -> editor.

Editor:
- texture list from RX3
- tap texture for preview
- export selected, or all if no selection
- import only after selecting a texture
- save as *_edited.rx3

Build:
1. Upload this folder to a GitHub repository.
2. Open Actions.
3. Run `Build Android APK`.
4. Download artifact `RX3-Texture-Editor-APK`.

Scope v0.1:
- RX3l texture chunks
- preview DXT1/DXT3/DXT5/RGBA8
- import RGBA8
- ChunLZMA and other FIFA-specific codecs still need to be added after testing against real samples.
