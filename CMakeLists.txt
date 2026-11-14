cmake_minimum_required(VERSION 3.22)
project(PadKeys VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Change this to an identifier under your own Apple Developer account before installing on a device.
set(PADKEYS_BUNDLE_ID "com.example.padkeys" CACHE STRING "Bundle identifier for the app")
set(JUCE_PATH "" CACHE PATH "Path to a local JUCE checkout (optional)")
option(PADKEYS_BUILD_TESTS "Build the offline render / screenshot test tool" OFF)

if(JUCE_PATH)
    add_subdirectory(${JUCE_PATH} juce)
else()
    include(FetchContent)
    FetchContent_Declare(JUCE
        GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
        GIT_TAG 8.0.15
        GIT_SHALLOW TRUE)
    FetchContent_MakeAvailable(JUCE)
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
    set(PADKEYS_FORMATS Standalone AUv3)
elseif(APPLE)
    set(PADKEYS_FORMATS AU Standalone)
else()
    set(PADKEYS_FORMATS Standalone)
endif()

set(PADKEYS_SOURCES
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp)

juce_add_plugin(PadKeys
    PRODUCT_NAME "PadKeys"
    COMPANY_NAME "PadKeys"
    BUNDLE_ID ${PADKEYS_BUNDLE_ID}
    PLUGIN_MANUFACTURER_CODE Pdky
    PLUGIN_CODE Pdk1
    FORMATS ${PADKEYS_FORMATS}
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    AU_MAIN_TYPE kAudioUnitType_MusicDevice
    BACKGROUND_AUDIO_ENABLED TRUE
    TARGETED_DEVICE_FAMILY "1,2"
    IPHONE_SCREEN_ORIENTATIONS UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight
    IPAD_SCREEN_ORIENTATIONS UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight
                             UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown)

target_sources(PadKeys PRIVATE ${PADKEYS_SOURCES})
target_compile_definitions(PadKeys PUBLIC
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(PadKeys
    PRIVATE juce::juce_audio_utils
    PUBLIC juce::juce_recommended_config_flags juce::juce_recommended_lto_flags)

if(PADKEYS_BUILD_TESTS)
    juce_add_console_app(PadKeysTest PRODUCT_NAME "PadKeysTest")
    target_sources(PadKeysTest PRIVATE test/Main.cpp ${PADKEYS_SOURCES})
    target_compile_definitions(PadKeysTest PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)
    target_link_libraries(PadKeysTest PRIVATE juce::juce_audio_utils juce::juce_recommended_config_flags)
endif()
