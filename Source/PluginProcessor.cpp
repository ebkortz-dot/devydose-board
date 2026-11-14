#include "PluginProcessor.h"
#include "PluginEditor.h"

namespace
{
    const char* const padNames[PadKeysProcessor::numPads] = {
        "Kick", "Rim", "Snare", "Clap", "Sub Kick", "Low Tom", "Hat", "Mid Tom",
        "Shaker", "High Tom", "Open Hat", "Cowbell", "Clave", "Crash", "Zap", "Ride" };

    const float padPan[PadKeysProcessor::numPads] = {
        0.0f, -0.15f, 0.0f, 0.1f, 0.0f, -0.35f, 0.25f, 0.0f,
        -0.3f, 0.35f, 0.25f, -0.25f, 0.3f, -0.2f, 0.15f, 0.3f };

    constexpr int hatClosedPad = 6, hatOpenPad = 10;

    juce::String pid (const char* base, int pad) { return juce::String (base) + juce::String (pad); }
}

const char* PadKeysProcessor::padName (int pad) { return padNames[juce::jlimit (0, numPads - 1, pad)]; }

juce::AudioProcessorValueTreeState::ParameterLayout PadKeysProcessor::createLayout()
{
    using FloatParam = juce::AudioParameterFloat;
    using ChoiceParam = juce::AudioParameterChoice;
    using Range = juce::NormalisableRange<float>;
    juce::AudioProcessorValueTreeState::ParameterLayout layout;

    auto skewed = [] (float lo, float hi, float centre)
    {
        Range r (lo, hi);
        r.setSkewForCentre (centre);
        return r;
    };

    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "master", 1 }, "Volume", Range (0.0f, 1.0f), 0.8f));
    layout.add (std::make_unique<ChoiceParam> (juce::ParameterID { "mode", 1 }, "Keyboard Mode",
                                               juce::StringArray { "Split", "Drums", "Keys" }, 0));

    for (int i = 0; i < numPads; ++i)
    {
        const juce::String name (padNames[i]);
        layout.add (std::make_unique<FloatParam> (juce::ParameterID { pid ("tune", i), 1 }, name + " Tune", Range (-12.0f, 12.0f), 0.0f));
        layout.add (std::make_unique<FloatParam> (juce::ParameterID { pid ("decay", i), 1 }, name + " Decay", skewed (0.25f, 3.0f, 1.0f), 1.0f));
        layout.add (std::make_unique<FloatParam> (juce::ParameterID { pid ("level", i), 1 }, name + " Level", Range (0.0f, 1.0f), 0.8f));
    }

    layout.add (std::make_unique<ChoiceParam> (juce::ParameterID { "wave", 1 }, "Keys Wave",
                                               juce::StringArray { "Saw", "Square", "Triangle", "Sine" }, 0));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "cutoff", 1 }, "Keys Cutoff", skewed (60.0f, 18000.0f, 1500.0f), 3500.0f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "reso", 1 }, "Keys Resonance", Range (0.0f, 1.0f), 0.2f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "attack", 1 }, "Keys Attack", skewed (0.002f, 2.0f, 0.2f), 0.005f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "decay", 1 }, "Keys Decay", skewed (0.01f, 3.0f, 0.4f), 0.35f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "sustain", 1 }, "Keys Sustain", Range (0.0f, 1.0f), 0.6f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "release", 1 }, "Keys Release", skewed (0.01f, 4.0f, 0.5f), 0.3f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "fat", 1 }, "Keys Fat", Range (0.0f, 1.0f), 0.4f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "keysLevel", 1 }, "Keys Level", Range (0.0f, 1.0f), 0.7f));

    layout.add (std::make_unique<ChoiceParam> (juce::ParameterID { "seqMode", 1 }, "Sequencer",
                                               juce::StringArray { "Off", "Song", "Free" }, 0));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "tempo", 1 }, "Free Tempo", Range (60.0f, 200.0f, 1.0f), 110.0f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "swing", 1 }, "Swing", Range (0.0f, 1.0f), 0.0f));

    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "fxFilter", 1 }, "Sweep Filter", Range (-1.0f, 1.0f), 0.0f));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "delayMix", 1 }, "Echo Mix", Range (0.0f, 1.0f), 0.0f));
    layout.add (std::make_unique<ChoiceParam> (juce::ParameterID { "delayTime", 1 }, "Echo Time",
                                               juce::StringArray { "1/16", "1/8", "1/8 Dot", "1/4" }, 2));
    layout.add (std::make_unique<FloatParam> (juce::ParameterID { "delayFb", 1 }, "Echo Repeats", Range (0.0f, 0.85f), 0.4f));

    return layout;
}

PadKeysProcessor::PadKeysProcessor()
    : AudioProcessor (BusesProperties().withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "PadKeys", createLayout())
{
    for (int i = 0; i < numPads; ++i)
    {
        const auto idx = (size_t) i;
        tuneParam[idx]  = apvts.getRawParameterValue (pid ("tune", i));
        decayParam[idx] = apvts.getRawParameterValue (pid ("decay", i));
        levelParam[idx] = apvts.getRawParameterValue (pid ("level", i));
        hitCount[idx].store (0);
        uiTrigger[idx].store (0.0f);
        pattern[idx].store (0);
    }

    // A starter beat so the sequencer does something the first time it is switched on.
    pattern[0].store (0x0581);   // kick
    pattern[2].store (0x1010);   // snare
    pattern[6].store (0x5555);   // hat
    pattern[10].store (0x4000);  // open hat

    masterParam    = apvts.getRawParameterValue ("master");
    modeParam      = apvts.getRawParameterValue ("mode");
    seqModeParam   = apvts.getRawParameterValue ("seqMode");
    tempoParam     = apvts.getRawParameterValue ("tempo");
    swingParam     = apvts.getRawParameterValue ("swing");
    fxFilterParam  = apvts.getRawParameterValue ("fxFilter");
    delayMixParam  = apvts.getRawParameterValue ("delayMix");
    delayTimeParam = apvts.getRawParameterValue ("delayTime");
    delayFbParam   = apvts.getRawParameterValue ("delayFb");

    keysParams.wave    = apvts.getRawParameterValue ("wave");
    keysParams.cutoff  = apvts.getRawParameterValue ("cutoff");
    keysParams.reso    = apvts.getRawParameterValue ("reso");
    keysParams.attack  = apvts.getRawParameterValue ("attack");
    keysParams.decay   = apvts.getRawParameterValue ("decay");
    keysParams.sustain = apvts.getRawParameterValue ("sustain");
    keysParams.release = apvts.getRawParameterValue ("release");
    keysParams.fat     = apvts.getRawParameterValue ("fat");
    keysParams.level   = apvts.getRawParameterValue ("keysLevel");

    synth.addSound (new KeysSound());
    for (int i = 0; i < 10; ++i)
        synth.addVoice (new KeysVoice (keysParams));
}

void PadKeysProcessor::prepareToPlay (double sampleRate, int)
{
    sr = sampleRate;

    for (int i = 0; i < numPads; ++i)
        drums[(size_t) i].prepare (sampleRate, (Drum) i);

    synth.setCurrentPlaybackSampleRate (sampleRate);
    keyboardState.reset();

    masterGain.reset (sampleRate, 0.03);
    masterGain.setCurrentAndTargetValue (masterParam->load());
    filterPos.reset (sampleRate, 0.05);
    filterPos.setCurrentAndTargetValue (fxFilterParam->load());
    delaySamplesSmoothed.reset (sampleRate, 0.25);
    delaySamplesSmoothed.setCurrentAndTargetValue ((float) (sampleRate * 0.3));

    delayBuffer.setSize (2, (int) (sampleRate * 2.5) + 8);
    delayBuffer.clear();
    delayWrite = 0;
    for (auto& f : fxFilter) f.reset();
    freePpq = 0.0;
}

bool PadKeysProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto out = layouts.getMainOutputChannelSet();
    return out == juce::AudioChannelSet::stereo() || out == juce::AudioChannelSet::mono();
}

void PadKeysProcessor::setStep (int pad, int step, bool on)
{
    auto& p = pattern[(size_t) pad];
    const uint32_t bit = 1u << step;
    p.store (on ? (p.load() | bit) : (p.load() & ~bit));
}

void PadKeysProcessor::clearPattern()
{
    for (auto& p : pattern)
        p.store (0);
}

void PadKeysProcessor::triggerPad (int pad, float velocity, int offset)
{
    if (pad == hatClosedPad)
        drums[(size_t) hatOpenPad].choke();

    drums[(size_t) pad].trigger (velocity, offset);
    hitCount[(size_t) pad].fetch_add (1);
}

void PadKeysProcessor::runSequencer (int numSamples)
{
    const int seqMode = (int) seqModeParam->load();
    double ppq = 0.0, bpm = (double) tempoParam->load();
    bool running = false;

    if (auto* head = getPlayHead())
    {
        if (auto pos = head->getPosition())
        {
            if (auto hostBpm = pos->getBpm())
                currentBpm = *hostBpm;

            if (seqMode == 1 && pos->getIsPlaying() && pos->getPpqPosition().hasValue())
            {
                ppq = *pos->getPpqPosition();
                bpm = currentBpm;
                running = true;
            }
        }
    }

    if (seqMode == 2)
    {
        ppq = freePpq;
        currentBpm = bpm;
        running = true;
        freePpq += numSamples * bpm / (60.0 * sr);
    }
    else
    {
        freePpq = 0.0;
    }

    if (! running || bpm <= 0.0)
    {
        currentStep.store (-1);
        return;
    }

    const double ppqPerSample = bpm / (60.0 * sr);
    const double ppqEnd = ppq + numSamples * ppqPerSample;
    const double swingDelay = (double) swingParam->load() * 0.25 / 3.0;

    for (auto k = (juce::int64) std::floor (ppq * 4.0) - 1; k <= (juce::int64) std::floor (ppqEnd * 4.0); ++k)
    {
        const double stepPpq = (double) k * 0.25 + ((k & 1) != 0 ? swingDelay : 0.0);

        if (stepPpq < ppq || stepPpq >= ppqEnd)
            continue;

        const int step = (int) (((k % numSteps) + numSteps) % numSteps);
        const int offset = juce::jlimit (0, numSamples - 1, (int) ((stepPpq - ppq) / ppqPerSample));

        for (int pad = 0; pad < numPads; ++pad)
            if ((pattern[(size_t) pad].load() >> step) & 1u)
                triggerPad (pad, 0.85f, offset);

        currentStep.store (step);
    }
}

void PadKeysProcessor::applyEffects (juce::AudioBuffer<float>& buffer, int numSamples)
{
    const int channels = juce::jmin (2, buffer.getNumChannels());
    const float sampleRate = (float) sr;

    // Echo, timed to the song tempo.
    static const float beats[4] = { 0.25f, 0.5f, 0.75f, 1.0f };
    const float mix = delayMixParam->load();
    const float feedback = delayFbParam->load();
    const int size = delayBuffer.getNumSamples();
    const float wanted = beats[juce::jlimit (0, 3, (int) delayTimeParam->load())] * 60.0f / (float) juce::jmax (30.0, currentBpm) * sampleRate;
    delaySamplesSmoothed.setTargetValue (juce::jlimit (16.0f, (float) size - 8.0f, wanted));

    filterPos.setTargetValue (fxFilterParam->load());

    for (int i = 0; i < numSamples; ++i)
    {
        const float d = delaySamplesSmoothed.getNextValue();
        float readPos = (float) delayWrite - d;
        if (readPos < 0) readPos += (float) size;
        const int i0 = (int) readPos;
        const int i1 = (i0 + 1) % size;
        const float frac = readPos - (float) i0;

        const float pos = filterPos.getNextValue();
        const bool filterOn = std::abs (pos) > 0.02f;

        if (filterOn && (i & 15) == 0)
        {
            const float freq = pos < 0 ? 18000.0f * std::pow (0.006f, -pos)     // sweep down: low-pass
                                       : 30.0f * std::pow (200.0f, pos);         // sweep up: high-pass
            for (auto& f : fxFilter)
                f.set (freq, 1.1f, sampleRate);
        }

        for (int ch = 0; ch < channels; ++ch)
        {
            auto* data = buffer.getWritePointer (ch);
            auto* line = delayBuffer.getWritePointer (ch);
            const float dry = data[i];
            const float echo = line[i0] + frac * (line[i1] - line[i0]);
            line[delayWrite] = dry + echo * feedback;
            float out = dry + echo * mix;

            if (filterOn)
            {
                float lp, bp, hp;
                fxFilter[ch].tick (out, lp, bp, hp);
                out = pos < 0 ? lp : hp;
            }

            data[i] = out;
        }

        if (++delayWrite >= size)
            delayWrite = 0;
    }
}

void PadKeysProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)
{
    juce::ScopedNoDenormals noDenormals;
    const int numSamples = buffer.getNumSamples();
    buffer.clear();

    if (numSamples == 0)
        return;

    for (int i = 0; i < numPads; ++i)
    {
        const auto idx = (size_t) i;
        drums[idx].setParams (tuneParam[idx]->load(), decayParam[idx]->load(), levelParam[idx]->load());
    }

    // Incoming notes: decide whether each one plays a drum pad or the keyboard synth.
    const int mode = (int) modeParam->load();   // 0 split, 1 drums, 2 keys
    synthMidi.clear();

    for (const auto meta : midi)
    {
        const auto msg = meta.getMessage();

        if (msg.isNoteOn())
        {
            const int note = msg.getNoteNumber();
            const bool inPadRange = note >= firstPadNote && note < firstPadNote + numPads;

            if (mode == 1 || (mode == 0 && inPadRange))
            {
                const int pad = (((note - firstPadNote) % numPads) + numPads) % numPads;
                triggerPad (pad, msg.getFloatVelocity(), juce::jlimit (0, numSamples - 1, meta.samplePosition));
                continue;
            }
        }

        synthMidi.addEvent (msg, meta.samplePosition);
    }

    midi.clear();
    keyboardState.processNextMidiBuffer (synthMidi, 0, numSamples, true);   // on-screen keys always play the synth

    for (int i = 0; i < numPads; ++i)
    {
        const float v = uiTrigger[(size_t) i].exchange (0.0f);
        if (v > 0.0f)
            triggerPad (i, v, 0);
    }

    runSequencer (numSamples);

    auto* left = buffer.getWritePointer (0);
    auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer (1) : nullptr;

    for (int pad = 0; pad < numPads; ++pad)
    {
        auto& voice = drums[(size_t) pad];
        if (! voice.isBusy())
            continue;

        const float gl = 1.0f - juce::jmax (0.0f, padPan[pad]);
        const float gr = 1.0f + juce::jmin (0.0f, padPan[pad]);

        for (int i = 0; i < numSamples; ++i)
        {
            const float s = voice.tick();
            left[i] += s * (right != nullptr ? gl : 1.0f);
            if (right != nullptr)
                right[i] += s * gr;
        }
    }

    synth.renderNextBlock (buffer, synthMidi, 0, numSamples);
    applyEffects (buffer, numSamples);

    masterGain.setTargetValue (masterParam->load());
    for (int i = 0; i < numSamples; ++i)
    {
        const float g = masterGain.getNextValue();
        const float gain = g * g * 1.4f;
        for (int ch = 0; ch < buffer.getNumChannels(); ++ch)
        {
            // Gentle limiter so stacked sounds never clip harshly.
            auto& v = buffer.getWritePointer (ch)[i];
            const float x = v * gain, mag = std::abs (x);
            v = mag <= 0.7f ? x : std::copysign (0.7f + 0.3f * std::tanh ((mag - 0.7f) / 0.3f), x);
        }
    }
}

void PadKeysProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    auto state = apvts.copyState();
    juce::StringArray rows;
    for (auto& p : pattern)
        rows.add (juce::String::toHexString ((int) p.load()));
    state.setProperty ("pattern", rows.joinIntoString (","), nullptr);

    if (auto xml = state.createXml())
        copyXmlToBinary (*xml, destData);
}

void PadKeysProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    if (auto xml = getXmlFromBinary (data, sizeInBytes))
    {
        auto state = juce::ValueTree::fromXml (*xml);
        if (! state.isValid())
            return;

        if (state.hasProperty ("pattern"))
        {
            auto rows = juce::StringArray::fromTokens (state["pattern"].toString(), ",", "");
            for (int i = 0; i < juce::jmin (numPads, rows.size()); ++i)
                pattern[(size_t) i].store ((uint32_t) rows[i].getHexValue32() & 0xffffu);
        }

        apvts.replaceState (state);
    }
}

juce::AudioProcessorEditor* PadKeysProcessor::createEditor() { return new PadKeysEditor (*this); }

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new PadKeysProcessor(); }
