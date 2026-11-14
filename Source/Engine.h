#pragma once
#include <juce_audio_basics/juce_audio_basics.h>
#include <atomic>
#include <cmath>

// ---------------------------------------------------------------------------
// Small state-variable filter (low / band / high-pass in one).
struct SVF
{
    float ic1 = 0, ic2 = 0, k = 1, a1 = 0, a2 = 0, a3 = 0;

    void set (float freq, float q, float sampleRate)
    {
        const float g = std::tan (juce::MathConstants<float>::pi * juce::jlimit (20.0f, sampleRate * 0.45f, freq) / sampleRate);
        k = 1.0f / q;
        a1 = 1.0f / (1.0f + g * (g + k));
        a2 = g * a1;
        a3 = g * a2;
    }

    void reset() { ic1 = ic2 = 0; }

    inline void tick (float in, float& lp, float& bp, float& hp)
    {
        const float v3 = in - ic2;
        const float v1 = a1 * ic1 + a2 * v3;
        const float v2 = ic2 + a2 * ic1 + a3 * v3;
        ic1 = 2.0f * v1 - ic1;
        ic2 = 2.0f * v2 - ic2;
        lp = v2; bp = v1; hp = in - k * v1 - v2;
    }
};

// ---------------------------------------------------------------------------
// The sixteen drum sounds, all synthesised (no sample files needed).
enum class Drum { Kick, Rim, Snare, Clap, Kick808, TomLow, HatClosed, TomMid,
                  Shaker, TomHigh, HatOpen, Cowbell, Clave, Crash, Zap, Ride };

class DrumVoice
{
public:
    void prepare (double sampleRate, Drum drumType)
    {
        sr = (float) sampleRate;
        type = drumType;
        active = false;
        pending = -1;
    }

    void setParams (float tuneSemitones, float decayAmount, float levelAmount)
    {
        tune = std::pow (2.0f, tuneSemitones / 12.0f);
        decay = decayAmount;
        level = levelAmount;
    }

    // Start the sound `delaySamples` from now.
    void trigger (float velocity, int delaySamples)
    {
        pendingVel = velocity;
        pending = juce::jmax (0, delaySamples);
    }

    void choke()
    {
        if (active)
            ampCoef = coef (0.006f);
    }

    bool isBusy() const { return active || pending >= 0; }

    inline float tick()
    {
        if (pending >= 0 && pending-- == 0)
            start (pendingVel);

        if (! active)
            return 0.0f;

        const float out = render() * gain;

        amp *= ampCoef;
        penv *= penvCoef;
        nenv *= nenvCoef;
        ++n;

        if (amp < 1.0e-4f && n > 64)
            active = false;

        return out;
    }

private:
    static constexpr float twoPi = juce::MathConstants<float>::twoPi;

    float coef (float seconds) const { return std::exp (-1.0f / (juce::jmax (0.0005f, seconds) * sr)); }

    float noise()
    {
        rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
        return (float) (int32_t) rng * (1.0f / 2147483648.0f);
    }

    float sine (int i, float freq)
    {
        ph[i] += freq / sr;
        if (ph[i] >= 1.0f) ph[i] -= 1.0f;
        return std::sin (twoPi * ph[i]);
    }

    float square (int i, float freq)
    {
        ph[i] += freq / sr;
        if (ph[i] >= 1.0f) ph[i] -= 1.0f;
        return ph[i] < 0.5f ? 1.0f : -1.0f;
    }

    // Six detuned square waves: the classic recipe for cymbals and hi-hats.
    float metal (float scale)
    {
        static const float f[6] = { 205.3f, 304.4f, 369.6f, 522.7f, 540.0f, 800.0f };
        float s = 0;
        for (int i = 0; i < 6; ++i)
            s += square (i, f[i] * scale * tune);
        return s * (1.0f / 6.0f);
    }

    void start (float velocity)
    {
        active = true;
        n = 0;
        amp = penv = nenv = 1.0f;
        for (auto& p : ph) p = 0;
        f1.reset(); f2.reset();
        gain = velocity * velocity * level;

        float a = 0.2f, p = 0.03f, nz = 0.01f;

        switch (type)
        {
            case Drum::Kick:      a = 0.26f; p = 0.030f; nz = 0.004f; break;
            case Drum::Kick808:   a = 0.85f; p = 0.050f; nz = 0.003f; break;
            case Drum::Snare:     a = 0.085f; p = 0.020f; nz = 0.150f; f1.set (1800.0f, 0.7f, sr); break;
            case Drum::Rim:       a = 0.020f; p = 0.010f; nz = 0.008f; f1.set (2600.0f, 2.0f, sr); break;
            case Drum::Clap:      a = 0.130f; nz = 0.130f; f1.set (1150.0f * tune, 2.2f, sr); break;
            case Drum::TomLow:    a = 0.36f; p = 0.060f; nz = 0.005f; break;
            case Drum::TomMid:    a = 0.30f; p = 0.055f; nz = 0.005f; break;
            case Drum::TomHigh:   a = 0.25f; p = 0.050f; nz = 0.005f; break;
            case Drum::HatClosed: a = 0.035f; f1.set (7000.0f, 0.8f, sr); break;
            case Drum::HatOpen:   a = 0.300f; f1.set (7000.0f, 0.8f, sr); break;
            case Drum::Shaker:    a = 0.050f; f1.set (5200.0f, 0.9f, sr); break;
            case Drum::Cowbell:   a = 0.220f; p = 0.015f; f1.set (800.0f * tune, 3.0f, sr); break;
            case Drum::Clave:     a = 0.032f; break;
            case Drum::Crash:     a = 1.100f; f1.set (3600.0f, 0.7f, sr); break;
            case Drum::Ride:      a = 0.700f; p = 0.020f; f1.set (6200.0f, 1.2f, sr); break;
            case Drum::Zap:       a = 0.150f; p = 0.040f; break;
        }

        ampCoef  = coef (a * decay);
        penvCoef = coef (type == Drum::Zap ? p * decay : p);
        nenvCoef = coef (type == Drum::Snare || type == Drum::Clap ? nz * decay : nz);
    }

    float render()
    {
        float lp, bp, hp;

        switch (type)
        {
            case Drum::Kick:
            {
                const float s = sine (0, 50.0f * tune * (1.0f + 3.6f * penv)) * amp + noise() * nenv * 0.25f;
                return std::tanh (s * 1.6f) * 0.95f;
            }
            case Drum::Kick808:
            {
                const float s = sine (0, 43.0f * tune * (1.0f + 2.2f * penv)) * amp + noise() * nenv * 0.15f;
                return std::tanh (s * 2.2f) * 0.85f;
            }
            case Drum::Snare:
            {
                const float body = (sine (0, 185.0f * tune * (1.0f + 0.5f * penv)) * 0.6f
                                  + sine (1, 330.0f * tune) * 0.35f) * amp;
                f1.tick (noise(), lp, bp, hp);
                return body * 0.8f + hp * nenv * 0.55f;
            }
            case Drum::Rim:
            {
                f1.tick (noise(), lp, bp, hp);
                return (sine (0, 1750.0f * tune) * 0.5f + sine (1, 480.0f * tune) * 0.5f) * amp + bp * nenv * 0.5f;
            }
            case Drum::Clap:
            {
                const float t = (float) n / sr;
                const float env = t < 0.033f ? std::exp (-std::fmod (t, 0.011f) / 0.004f)
                                             : amp * 1.3f;
                f1.tick (noise(), lp, bp, hp);
                return bp * env * 1.3f;
            }
            case Drum::TomLow:   return tom (88.0f);
            case Drum::TomMid:   return tom (128.0f);
            case Drum::TomHigh:  return tom (178.0f);
            case Drum::HatClosed:
            case Drum::HatOpen:
            {
                f1.tick (metal (1.0f) * 0.8f + noise() * 0.25f, lp, bp, hp);
                return hp * amp * 1.7f;
            }
            case Drum::Shaker:
            {
                const float attack = juce::jmin (1.0f, (float) n / (0.008f * sr));
                f1.tick (noise(), lp, bp, hp);
                return hp * amp * attack * 0.6f;
            }
            case Drum::Cowbell:
            {
                f1.tick (square (0, 540.0f * tune) + square (1, 800.0f * tune), lp, bp, hp);
                return bp * (0.6f * penv + 0.4f * amp) * 0.24f;
            }
            case Drum::Clave:
                return sine (0, 2500.0f * tune) * amp * 0.7f;
            case Drum::Crash:
            {
                f1.tick (metal (1.5f) * 0.6f + noise() * 0.5f, lp, bp, hp);
                return hp * amp * 0.75f;
            }
            case Drum::Ride:
            {
                f1.tick (metal (2.1f), lp, bp, hp);
                return (bp * 0.9f + hp * 0.3f) * (0.5f * penv + 0.5f * amp) * 1.5f;
            }
            case Drum::Zap:
                return sine (0, 90.0f * tune + 5000.0f * penv * penv) * amp * 0.6f;
        }

        return 0.0f;
    }

    float tom (float freq)
    {
        return (sine (0, freq * tune * (1.0f + 0.8f * penv)) * amp + noise() * nenv * 0.15f) * 0.85f;
    }

    Drum type = Drum::Kick;
    float sr = 44100.0f;
    float tune = 1.0f, decay = 1.0f, level = 0.8f, gain = 0.0f;
    float amp = 0, penv = 0, nenv = 0, ampCoef = 0, penvCoef = 0, nenvCoef = 0;
    float ph[6] = {};
    SVF f1, f2;
    uint32_t rng = 0x12345678u;
    int n = 0, pending = -1;
    float pendingVel = 0;
    bool active = false;
};

// ---------------------------------------------------------------------------
// Keyboard synth: two detuned oscillators -> low-pass filter -> ADSR envelope.
struct KeysParams
{
    std::atomic<float>* wave = nullptr, *cutoff = nullptr, *reso = nullptr, *attack = nullptr, *decay = nullptr,
                      * sustain = nullptr, *release = nullptr, *fat = nullptr, *level = nullptr;
};

struct KeysSound : juce::SynthesiserSound
{
    bool appliesToNote (int) override    { return true; }
    bool appliesToChannel (int) override { return true; }
};

class KeysVoice : public juce::SynthesiserVoice
{
public:
    explicit KeysVoice (const KeysParams& p) : params (p) {}

    bool canPlaySound (juce::SynthesiserSound*) override { return true; }

    void startNote (int midiNote, float velocity, juce::SynthesiserSound*, int pitchWheel) override
    {
        baseFreq = (float) juce::MidiMessage::getMidiNoteInHertz (midiNote);
        vel = 0.25f + 0.75f * velocity;
        pitchWheelMoved (pitchWheel);

        if (! adsr.isActive())
        {
            filter.reset();
            ph1 = 0.0f; ph2 = 0.37f;
        }

        updateEnvelope();
        adsr.noteOn();
    }

    void stopNote (float, bool allowTailOff) override
    {
        if (allowTailOff)
        {
            adsr.noteOff();
        }
        else
        {
            adsr.reset();
            clearCurrentNote();
        }
    }

    void pitchWheelMoved (int value) override
    {
        bend = std::pow (2.0f, 2.0f * ((float) value - 8192.0f) / 8192.0f / 12.0f);
    }

    void controllerMoved (int, int) override {}

    void setCurrentPlaybackSampleRate (double newRate) override
    {
        juce::SynthesiserVoice::setCurrentPlaybackSampleRate (newRate);
        if (newRate > 0)
            adsr.setSampleRate (newRate);
    }

    void renderNextBlock (juce::AudioBuffer<float>& buffer, int startSample, int numSamples) override
    {
        if (! adsr.isActive())
            return;

        const float sr = (float) getSampleRate();
        const int wave = (int) params.wave->load();
        const float cutoff = params.cutoff->load();
        const float q = 0.6f + params.reso->load() * 7.0f;
        const float detune = std::pow (2.0f, params.fat->load() * 22.0f / 1200.0f);
        const float level = params.level->load() * vel * 0.4f;
        const float dt1 = baseFreq * bend * detune / sr;
        const float dt2 = baseFreq * bend / detune / sr;
        updateEnvelope();

        auto* left = buffer.getWritePointer (0);
        auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer (1) : nullptr;

        for (int i = 0; i < numSamples; ++i)
        {
            const float env = adsr.getNextSample();

            if ((i & 15) == 0)
                filter.set (cutoff * (0.3f + 0.7f * env), q, sr);

            const float osc = 0.5f * (oscillator (wave, ph1, dt1) + oscillator (wave, ph2, dt2));
            float lp, bp, hp;
            filter.tick (osc, lp, bp, hp);
            const float out = lp * env * level;

            left[startSample + i] += out;
            if (right != nullptr)
                right[startSample + i] += out;
        }

        if (! adsr.isActive())
            clearCurrentNote();
    }

private:
    static float polyBlep (float t, float dt)
    {
        if (t < dt)        { t /= dt; return t + t - t * t - 1.0f; }
        if (t > 1.0f - dt) { t = (t - 1.0f) / dt; return t * t + t + t + 1.0f; }
        return 0.0f;
    }

    static float oscillator (int wave, float& ph, float dt)
    {
        ph += dt;
        if (ph >= 1.0f) ph -= 1.0f;

        switch (wave)
        {
            case 0:  return 2.0f * ph - 1.0f - polyBlep (ph, dt);                           // saw
            case 1:  { float t2 = ph + 0.5f; if (t2 >= 1.0f) t2 -= 1.0f;                     // square
                       return (ph < 0.5f ? 1.0f : -1.0f) + polyBlep (ph, dt) - polyBlep (t2, dt); }
            case 2:  return 4.0f * std::abs (ph - 0.5f) - 1.0f;                              // triangle
            default: return std::sin (juce::MathConstants<float>::twoPi * ph);               // sine
        }
    }

    void updateEnvelope()
    {
        adsr.setParameters ({ params.attack->load(), params.decay->load(),
                              params.sustain->load(), params.release->load() });
    }

    const KeysParams& params;
    juce::ADSR adsr;
    SVF filter;
    float baseFreq = 440.0f, bend = 1.0f, vel = 1.0f, ph1 = 0.0f, ph2 = 0.37f;
};
