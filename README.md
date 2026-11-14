# PadKeys

A drum machine + keyboard synth instrument for GarageBand on iPad / iPhone (AUv3), which also runs as its own app.
All sounds are synthesised in code; there are no sample files.

- **PADS** – 16 touch pads (tap high on a pad for a hard hit, low for a soft one). Each pad has Tune and Length dials and a Level slider.
- **STEPS** – 16-step beat sequencer. `Song` follows GarageBand's play button and tempo; `Free` runs on its own Tempo dial.
- **KEYS** – polyphonic synth: wave shape, tone, edge, attack / decay / sustain / release, fat, level, plus an on-screen keyboard.
- **FX** – sweep-filter slider and a tempo-synced echo.
- **Split / Drums / Keys** – how incoming notes are routed. Split: C1–D#2 play pads, everything else plays the synth.

## Building

Needs a Mac with Xcode and CMake (JUCE 8 is downloaded automatically).

    cmake -B build-ios -G Xcode -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_DEPLOYMENT_TARGET=15.0 \
          -DPADKEYS_BUNDLE_ID=com.yourname.padkeys
    open build-ios/PadKeys.xcodeproj

In Xcode pick your team under Signing for both the `PadKeys - Standalone Plugin` and `PadKeys - AUv3 AppExtension`
targets, select your iPad, and press Run. Open the app once, then in GarageBand add a track:
External → Audio Unit Extensions → PadKeys.

`test/Main.cpp` is an offline check (build with `-DPADKEYS_BUILD_TESTS=ON`): it renders every sound, runs the
sequencer, and writes a demo WAV and screenshots.

JUCE is used under its AGPLv3 / JUCE licence terms; check those before distributing or selling the app.
