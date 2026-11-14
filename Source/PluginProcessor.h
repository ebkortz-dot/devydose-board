#pragma once
#include <juce_audio_utils/juce_audio_utils.h>
#include "Engine.h"

class PadKeysProcessor : public juce::AudioProcessor
{
public:
    static constexpr int numPads = 16, numSteps = 16, firstPadNote = 36;

    PadKeysProcessor();
    ~PadKeysProcessor() override = default;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override {}
    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override                        { return true; }

    const juce::String getName() const override            { return "PadKeys"; }
    bool acceptsMidi() const override                      { return true; }
    bool producesMidi() const override                     { return false; }
    bool isMidiEffect() const override                     { return false; }
    double getTailLengthSeconds() const override           { return 2.0; }

    int getNumPrograms() override                          { return 1; }
    int getCurrentProgram() override                       { return 0; }
    void setCurrentProgram (int) override                  {}
    const juce::String getProgramName (int) override       { return {}; }
    void changeProgramName (int, const juce::String&) override {}

    void getStateInformation (juce::MemoryBlock& destData) override;
    void setStateInformation (const void* data, int sizeInBytes) override;

    // --- used by the screen ---
    static const char* padName (int pad);
    void hitPad (int pad, float velocity)                  { uiTrigger[(size_t) pad].store (velocity); }
    bool getStep (int pad, int step) const                 { return (pattern[(size_t) pad].load() >> step) & 1u; }
    void setStep (int pad, int step, bool on);
    void clearPattern();

    // Which parameter each of the three "assignable" controls on the Play screen drives.
    juce::String getAssignment (int slot) const;
    void setAssignment (int slot, const juce::String& paramID);

    juce::AudioProcessorValueTreeState apvts;
    juce::MidiKeyboardState keyboardState;
    std::array<std::atomic<uint32_t>, numPads> hitCount;
    std::atomic<int> currentStep { -1 };

private:
    static juce::AudioProcessorValueTreeState::ParameterLayout createLayout();
    void triggerPad (int pad, float velocity, int offset);
    void runSequencer (int numSamples);
    void applyEffects (juce::AudioBuffer<float>&, int numSamples);

    std::array<DrumVoice, numPads> drums;
    std::array<std::atomic<uint32_t>, numPads> pattern;
    std::array<std::atomic<float>, numPads> uiTrigger;
    std::array<std::atomic<float>*, numPads> tuneParam {}, decayParam {}, levelParam {};

    juce::Synthesiser synth;
    KeysParams keysParams;
    juce::MidiBuffer synthMidi;

    std::atomic<float>* masterParam = nullptr, *modeParam = nullptr, *seqModeParam = nullptr, *tempoParam = nullptr,
                      * swingParam = nullptr, *fxFilterParam = nullptr, *delayMixParam = nullptr,
                      * delayTimeParam = nullptr, *delayFbParam = nullptr;

    juce::SmoothedValue<float> masterGain, filterPos, delaySamplesSmoothed;
    juce::AudioBuffer<float> delayBuffer;
    int delayWrite = 0;
    SVF fxFilter[2];

    double sr = 44100.0, freePpq = 0.0, currentBpm = 120.0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PadKeysProcessor)
};
