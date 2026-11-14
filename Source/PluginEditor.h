#pragma once
#include "PluginProcessor.h"

namespace pk
{
    const juce::Colour background { 0xff14161b }, panel { 0xff20242c }, panelLight { 0xff2c313b },
                       accent { 0xffffb020 }, text { 0xffe9e9ec }, dim { 0xff8b909b };

    inline juce::Colour padColour (int pad)
    {
        static const juce::uint32 c[16] = {
            0xffff5a4d, 0xffffb020, 0xffffb020, 0xffffb020, 0xffff5a4d, 0xff9a7bff, 0xff37c8d8, 0xff9a7bff,
            0xff5fd068, 0xff9a7bff, 0xff37c8d8, 0xff5fd068, 0xff5fd068, 0xff37c8d8, 0xffff6fb5, 0xff37c8d8 };
        return juce::Colour (c[juce::jlimit (0, 15, pad)]);
    }

    // ----------------------------------------------------------------------
    class Look : public juce::LookAndFeel_V4
    {
    public:
        Look();
        void drawRotarySlider (juce::Graphics&, int x, int y, int w, int h, float pos, float startAngle,
                               float endAngle, juce::Slider&) override;
        void drawLinearSlider (juce::Graphics&, int x, int y, int w, int h, float pos, float minPos, float maxPos,
                               juce::Slider::SliderStyle, juce::Slider&) override;
    };

    // ----------------------------------------------------------------------
    // A dial with a caption under it.
    class Knob : public juce::Component
    {
    public:
        explicit Knob (const juce::String& caption);
        void attach (juce::AudioProcessorValueTreeState&, const juce::String& paramID);
        void resized() override;

        juce::Slider slider { juce::Slider::RotaryHorizontalVerticalDrag, juce::Slider::NoTextBox };
        juce::Label label;

    private:
        std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> attachment;
    };

    // ----------------------------------------------------------------------
    // A row of touch-friendly choices (used instead of drop-down menus).
    class Segmented : public juce::Component
    {
    public:
        Segmented (juce::RangedAudioParameter&, const juce::StringArray& names);
        void paint (juce::Graphics&) override;
        void mouseDown (const juce::MouseEvent&) override;

    private:
        juce::StringArray items;
        int index = 0;
        juce::ParameterAttachment attachment;
    };

    // ----------------------------------------------------------------------
    class PadButton : public juce::Component
    {
    public:
        void paint (juce::Graphics&) override;
        void mouseDown (const juce::MouseEvent&) override;

        std::function<void (float velocity)> onHit;
        int pad = 0;
        bool selected = false;
        float flash = 0.0f;
    };

    // ----------------------------------------------------------------------
    // A dial or slider whose target can be changed: tap its name to pick what it controls.
    class Assignable : public juce::Component
    {
    public:
        Assignable (PadKeysProcessor&, int slot, juce::Slider::SliderStyle);
        void resized() override;

        juce::Slider slider;

    private:
        void setTarget (const juce::String& paramID, bool save);
        void showMenu();

        PadKeysProcessor& processor;
        int slot;
        juce::String target;
        juce::TextButton caption;
        std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> attachment;
    };

    // ----------------------------------------------------------------------
    // Eight pads x sixteen steps. Tap squares to build a beat.
    class StepGrid : public juce::Component
    {
    public:
        explicit StepGrid (PadKeysProcessor& p) : processor (p) {}
        void paint (juce::Graphics&) override;
        void mouseDown (const juce::MouseEvent&) override;
        void mouseDrag (const juce::MouseEvent&) override;

        std::function<void (int pad)> onPadLabel;
        int page = 0, currentStep = -1, selectedPad = 0;

    private:
        static constexpr int rows = 8;
        int labelWidth() const { return juce::jlimit (48, 92, getWidth() / 7); }
        bool cellAt (juce::Point<int>, int& pad, int& step) const;

        PadKeysProcessor& processor;
        bool paintValue = true;
    };
}

// ==========================================================================
class PadKeysEditor : public juce::AudioProcessorEditor, private juce::Timer
{
public:
    explicit PadKeysEditor (PadKeysProcessor&);
    ~PadKeysEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

    void showTab (int tab);
    void selectPad (int pad);

private:
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    void timerCallback() override;
    void setPadBank (int bank);
    std::vector<juce::Component*> tabComponents (int tab);
    void styleCaption (juce::Label&, const juce::String&, juce::Justification = juce::Justification::centred);

    PadKeysProcessor& processor;
    pk::Look look;
    int currentTab = 0, selectedPad = 0;
    std::array<uint32_t, PadKeysProcessor::numPads> lastHit {};

    // top bar
    juce::Label title, volumeCaption;
    juce::TextButton tabButtons[5];
    pk::Segmented modeSwitch;
    juce::Slider masterSlider { juce::Slider::LinearHorizontal, juce::Slider::NoTextBox };
    SliderAttachment masterAttachment;

    // play tab: pads over a keyboard, plus three assignable controls
    pk::PadButton playPads[8];
    juce::TextButton bankButton { "PADS 1-8" };
    pk::Assignable assignDial1, assignDial2, assignSlider;
    juce::MidiKeyboardComponent playKeyboard;
    int padBank = 0;

    // pads tab
    pk::PadButton pads[PadKeysProcessor::numPads];
    juce::Label padTitle, levelCaption;
    pk::Knob tuneKnob { "TUNE" }, lengthKnob { "LENGTH" };
    juce::Slider levelSlider { juce::Slider::LinearVertical, juce::Slider::NoTextBox };
    std::unique_ptr<SliderAttachment> levelAttachment;

    // steps tab
    pk::StepGrid grid;
    pk::Segmented seqSwitch;
    pk::Knob tempoKnob { "TEMPO" }, swingKnob { "SWING" };
    juce::TextButton pageButton { "PADS 1-8" }, clearButton { "CLEAR" };

    // keys tab
    pk::Segmented waveSwitch;
    pk::Knob cutoffKnob { "TONE" }, resoKnob { "EDGE" }, attackKnob { "ATTACK" }, decayKnob { "DECAY" },
             sustainKnob { "SUSTAIN" }, releaseKnob { "RELEASE" }, fatKnob { "FAT" }, keysLevelKnob { "LEVEL" };
    juce::MidiKeyboardComponent keyboard;

    // fx tab
    juce::Label sweepCaption, echoCaption;
    juce::Slider sweepSlider { juce::Slider::LinearHorizontal, juce::Slider::NoTextBox };
    SliderAttachment sweepAttachment;
    pk::Segmented echoTimeSwitch;
    pk::Knob echoMixKnob { "ECHO" }, echoRepeatKnob { "REPEATS" };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PadKeysEditor)
};
