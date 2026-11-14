// Offline check: renders every sound, runs the sequencer, saves a demo WAV and screenshots.
#include "../Source/PluginProcessor.h"
#include "../Source/PluginEditor.h"

static int failures = 0;
static void check (bool ok, const juce::String& what)
{
    std::cout << (ok ? "PASS  " : "FAIL  ") << what << std::endl;
    if (! ok) ++failures;
}

struct Stats { float peak = 0; double sumSq = 0; juce::int64 n = 0; bool finite = true; };

static void render (PadKeysProcessor& p, juce::MidiBuffer& midi, int blocks, Stats& st, juce::AudioBuffer<float>* record = nullptr)
{
    juce::AudioBuffer<float> buf (2, 512);
    for (int b = 0; b < blocks; ++b)
    {
        p.processBlock (buf, midi);
        midi.clear();
        for (int ch = 0; ch < 2; ++ch)
            for (int i = 0; i < 512; ++i)
            {
                const float v = buf.getSample (ch, i);
                if (! std::isfinite (v)) st.finite = false;
                st.peak = juce::jmax (st.peak, std::abs (v));
                st.sumSq += v * v; ++st.n;
            }
        if (record != nullptr)
        {
            const int at = record->getNumSamples();
            record->setSize (2, at + 512, true);
            for (int ch = 0; ch < 2; ++ch) record->copyFrom (ch, at, buf, ch, 0, 512);
        }
    }
}

static void setParam (PadKeysProcessor& p, const char* id, float realValue)
{
    auto* param = p.apvts.getParameter (id);
    param->setValueNotifyingHost (param->convertTo0to1 (realValue));
}

int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI gui;
    const juce::File outDir (argc > 1 ? juce::File::getCurrentWorkingDirectory().getChildFile (argv[1])
                                      : juce::File::getCurrentWorkingDirectory());
    outDir.createDirectory();
    const double sr = 48000.0;

    {
        PadKeysProcessor p;
        p.setPlayConfigDetails (0, 2, sr, 512);
        p.prepareToPlay (sr, 512);
        juce::MidiBuffer midi;

        for (int pad = 0; pad < PadKeysProcessor::numPads; ++pad)
        {
            Stats st;
            midi.addEvent (juce::MidiMessage::noteOn (1, 36 + pad, 0.9f), 10);
            render (p, midi, 200, st);
            std::cout << juce::String (PadKeysProcessor::padName (pad)).paddedRight (' ', 10)
                      << " peak " << juce::String (st.peak, 3) << "  rms " << juce::String (std::sqrt (st.sumSq / (double) st.n), 4) << std::endl;
            check (st.finite && st.peak > 0.05f && st.peak < 1.2f, juce::String ("pad sound ") + PadKeysProcessor::padName (pad));
        }

        { Stats st; render (p, midi, 1000, st); Stats st2; render (p, midi, 20, st2); check (st2.peak < 1.0e-3f, "drums fall silent"); }

        for (int wave = 0; wave < 4; ++wave)
        {
            setParam (p, "wave", (float) wave);
            Stats st;
            for (int n : { 60, 64, 67 }) midi.addEvent (juce::MidiMessage::noteOn (1, n, 0.8f), 0);
            render (p, midi, 60, st);
            for (int n : { 60, 64, 67 }) midi.addEvent (juce::MidiMessage::noteOff (1, n), 0);
            Stats tail; render (p, midi, 500, tail);
            Stats quiet; render (p, midi, 20, quiet);
            std::cout << "keys wave " << wave << " peak " << st.peak << std::endl;
            check (st.finite && st.peak > 0.05f && st.peak < 1.2f && quiet.peak < 1.0e-3f, "keys chord, wave " + juce::String (wave));
        }

        // Split: note 60 must NOT hit a pad; Drums mode: it must.
        auto before = p.hitCount[8].load();
        midi.addEvent (juce::MidiMessage::noteOn (1, 60, 0.8f), 0); midi.addEvent (juce::MidiMessage::noteOff (1, 60), 100);
        { Stats st; render (p, midi, 4, st); }
        check (p.hitCount[8].load() == before, "split mode keeps middle C on the synth");
        setParam (p, "mode", 1.0f);
        midi.addEvent (juce::MidiMessage::noteOn (1, 60, 0.8f), 0);
        { Stats st; render (p, midi, 4, st); }
        check (p.hitCount[8].load() == before + 1, "drums mode maps every key to a pad");
        setParam (p, "mode", 0.0f);

        // Sequencer, free-running at 120 bpm for exactly 2 bars (4 s): 8 hat hits per bar.
        { Stats st; render (p, midi, 400, st); }
        const auto hat0 = p.hitCount[6].load(), kick0 = p.hitCount[0].load();
        setParam (p, "tempo", 120.0f);
        setParam (p, "seqMode", 2.0f);
        setParam (p, "wave", 0.0f);
        setParam (p, "delayMix", 0.25f);
        juce::AudioBuffer<float> demo (2, 0);
        Stats st;
        const int blocksPerBar = (int) (2.0 * sr / 512.0);
        for (int bar = 0; bar < 4; ++bar)
        {
            static const int chords[4][3] = { { 57, 60, 64 }, { 53, 57, 60 }, { 48, 52, 55 }, { 55, 59, 62 } };
            for (int n : chords[bar]) midi.addEvent (juce::MidiMessage::noteOn (1, n, 0.7f), 0);
            render (p, midi, blocksPerBar - 20, st, &demo);
            for (int n : chords[bar]) midi.addEvent (juce::MidiMessage::noteOff (1, n), 0);
            render (p, midi, 20, st, &demo);
        }
        const auto hats = p.hitCount[6].load() - hat0, kicks = p.hitCount[0].load() - kick0;
        std::cout << "sequencer: " << hats << " hats, " << kicks << " kicks, mix peak " << st.peak << std::endl;
        check (hats >= 31 && hats <= 32 && kicks >= 15 && kicks <= 16, "sequencer plays the pattern in time");
        check (st.finite && st.peak < 1.0f, "full mix stays below clipping");
        setParam (p, "seqMode", 0.0f);
        render (p, midi, 300, st, &demo);

        juce::WavAudioFormat wav;
        auto file = outDir.getChildFile ("padkeys-demo.wav");
        file.deleteFile();
        if (auto stream = file.createOutputStream())
            if (auto* writer = wav.createWriterFor (stream.release(), sr, 2, 16, {}, 0))
            {
                writer->writeFromAudioSampleBuffer (demo, 0, demo.getNumSamples());
                delete writer;
            }

        // Save / restore.
        p.setStep (3, 5, true);
        setParam (p, "tune3", 7.0f);
        juce::MemoryBlock state;
        p.getStateInformation (state);
        PadKeysProcessor q;
        q.setStateInformation (state.getData(), (int) state.getSize());
        check (q.getStep (3, 5) && q.getStep (0, 0) && ! q.getStep (3, 6)
               && std::abs (q.apvts.getRawParameterValue ("tune3")->load() - 7.0f) < 0.01f, "settings and beat survive save / reload");

        // Screenshots at an iPad-in-GarageBand size, a desktop size and a phone size.
        struct Size { int w, h; const char* name; };
        for (auto size : { Size { 1024, 340, "ipad" }, Size { 940, 440, "default" }, Size { 660, 230, "phone" } })
        {
            std::unique_ptr<juce::AudioProcessorEditor> ed (p.createEditor());
            auto* editor = dynamic_cast<PadKeysEditor*> (ed.get());
            editor->setSize (size.w, size.h);
            for (int tab = 0; tab < 4; ++tab)
            {
                editor->showTab (tab);
                auto image = editor->createComponentSnapshot (editor->getLocalBounds(), true, 2.0f);
                auto png = outDir.getChildFile (juce::String ("ui-") + size.name + "-" + juce::String (tab) + ".png");
                png.deleteFile();
                juce::FileOutputStream os (png);
                juce::PNGImageFormat().writeImageToStream (image, os);
            }
        }
        check (true, "screens drawn");
    }

    std::cout << (failures == 0 ? "ALL PASSED" : "FAILURES: " + juce::String (failures)) << std::endl;
    return failures;
}
