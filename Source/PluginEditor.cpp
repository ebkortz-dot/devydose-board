#include "PluginEditor.h"

namespace pk
{
Look::Look()
{
    setColour (juce::ResizableWindow::backgroundColourId, background);
    setColour (juce::Label::textColourId, text);
    setColour (juce::TextButton::buttonColourId, panel);
    setColour (juce::TextButton::buttonOnColourId, accent);
    setColour (juce::TextButton::textColourOffId, text);
    setColour (juce::TextButton::textColourOnId, juce::Colours::black);
    setColour (juce::ComboBox::outlineColourId, juce::Colours::transparentBlack);
    setColour (juce::BubbleComponent::backgroundColourId, panelLight);
    setColour (juce::TooltipWindow::textColourId, text);
    setColour (juce::MidiKeyboardComponent::keyDownOverlayColourId, accent);
    setColour (juce::MidiKeyboardComponent::mouseOverKeyOverlayColourId, accent.withAlpha (0.25f));
    setColour (juce::MidiKeyboardComponent::whiteNoteColourId, juce::Colour (0xfff2f0ea));
    setColour (juce::MidiKeyboardComponent::blackNoteColourId, juce::Colour (0xff17191e));
    setColour (juce::MidiKeyboardComponent::keySeparatorLineColourId, juce::Colour (0xff50545c));
}

void Look::drawRotarySlider (juce::Graphics& g, int x, int y, int w, int h, float pos, float startAngle,
                             float endAngle, juce::Slider& slider)
{
    auto area = juce::Rectangle<int> (x, y, w, h).toFloat().reduced (3.0f);
    const float radius = juce::jmin (area.getWidth(), area.getHeight()) * 0.5f;
    const auto centre = area.getCentre();
    const float thickness = juce::jlimit (3.0f, 7.0f, radius * 0.16f);
    const float arcRadius = radius - thickness * 0.5f;
    const float angle = startAngle + pos * (endAngle - startAngle);
    const juce::PathStrokeType stroke (thickness, juce::PathStrokeType::curved, juce::PathStrokeType::rounded);

    juce::Path track;
    track.addCentredArc (centre.x, centre.y, arcRadius, arcRadius, 0.0f, startAngle, endAngle, true);
    g.setColour (panelLight);
    g.strokePath (track, stroke);

    juce::Path value;
    value.addCentredArc (centre.x, centre.y, arcRadius, arcRadius, 0.0f, startAngle, angle, true);
    g.setColour (slider.isEnabled() ? accent : dim);
    g.strokePath (value, stroke);

    const float bodyRadius = arcRadius - thickness * 1.3f;
    if (bodyRadius > 2.0f)
    {
        g.setGradientFill (juce::ColourGradient (juce::Colour (0xff474d59), centre.x, centre.y - bodyRadius,
                                                 juce::Colour (0xff23272f), centre.x, centre.y + bodyRadius, false));
        g.fillEllipse (juce::Rectangle<float> (bodyRadius * 2.0f, bodyRadius * 2.0f).withCentre (centre));

        juce::Path pointer;
        pointer.addRoundedRectangle (-thickness * 0.35f, -bodyRadius * 0.92f, thickness * 0.7f, bodyRadius * 0.5f, thickness * 0.35f);
        g.setColour (text);
        g.fillPath (pointer, juce::AffineTransform::rotation (angle).translated (centre));
    }
}

void Look::drawLinearSlider (juce::Graphics& g, int x, int y, int w, int h, float pos, float, float,
                             juce::Slider::SliderStyle style, juce::Slider& slider)
{
    const bool vertical = style == juce::Slider::LinearVertical;
    const bool fromCentre = (bool) slider.getProperties().getWithDefault ("fromCentre", false);
    auto area = juce::Rectangle<int> (x, y, w, h).toFloat();
    const float trackSize = juce::jlimit (6.0f, 14.0f, (vertical ? area.getWidth() : area.getHeight()) * 0.3f);

    auto track = vertical ? area.withSizeKeepingCentre (trackSize, area.getHeight())
                          : area.withSizeKeepingCentre (area.getWidth(), trackSize);
    g.setColour (panelLight);
    g.fillRoundedRectangle (track, trackSize * 0.5f);

    juce::Rectangle<float> fill;
    if (vertical)
        fill = track.withTop (pos);
    else if (fromCentre)
        fill = track.withLeft (juce::jmin (pos, track.getCentreX())).withRight (juce::jmax (pos, track.getCentreX()));
    else
        fill = track.withRight (pos);

    g.setColour (accent);
    g.fillRoundedRectangle (fill, trackSize * 0.5f);

    const float thumbLong = juce::jmin (vertical ? area.getWidth() : area.getHeight(), 40.0f);
    const float thumbShort = juce::jlimit (12.0f, 20.0f, thumbLong * 0.5f);
    auto thumb = vertical ? juce::Rectangle<float> (thumbLong, thumbShort).withCentre ({ area.getCentreX(), pos })
                          : juce::Rectangle<float> (thumbShort, thumbLong).withCentre ({ pos, area.getCentreY() });
    g.setColour (text);
    g.fillRoundedRectangle (thumb, 4.0f);
    g.setColour (background);
    if (vertical)
        g.fillRect (thumb.withSizeKeepingCentre (thumb.getWidth() * 0.6f, 2.0f));
    else
        g.fillRect (thumb.withSizeKeepingCentre (2.0f, thumb.getHeight() * 0.6f));
}

// --------------------------------------------------------------------------
Knob::Knob (const juce::String& caption)
{
    label.setText (caption, juce::dontSendNotification);
    label.setJustificationType (juce::Justification::centred);
    label.setColour (juce::Label::textColourId, dim);
    label.setMinimumHorizontalScale (0.6f);
    label.setInterceptsMouseClicks (false, false);
    addAndMakeVisible (slider);
    addAndMakeVisible (label);
}

void Knob::attach (juce::AudioProcessorValueTreeState& state, const juce::String& paramID)
{
    attachment.reset();
    attachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment> (state, paramID, slider);
    if (auto* p = state.getParameter (paramID))
        slider.setDoubleClickReturnValue (true, p->convertFrom0to1 (p->getDefaultValue()));
}

void Knob::resized()
{
    auto r = getLocalBounds();
    const int labelH = juce::jlimit (12, 18, getHeight() / 4);
    label.setFont (juce::FontOptions ((float) labelH - 2.0f, juce::Font::bold));
    label.setBounds (r.removeFromBottom (labelH));
    slider.setBounds (r);
}

// --------------------------------------------------------------------------
Segmented::Segmented (juce::RangedAudioParameter& p, const juce::StringArray& names)
    : items (names),
      attachment (p, [this] (float v) { index = juce::roundToInt (v); repaint(); }, nullptr)
{
    attachment.sendInitialUpdate();
}

void Segmented::paint (juce::Graphics& g)
{
    auto area = getLocalBounds().toFloat();
    g.setColour (panel);
    g.fillRoundedRectangle (area, 7.0f);

    const float w = area.getWidth() / (float) items.size();
    g.setFont (juce::FontOptions (juce::jlimit (10.0f, 15.0f, area.getHeight() * 0.42f), juce::Font::bold));

    for (int i = 0; i < items.size(); ++i)
    {
        auto cell = juce::Rectangle<float> (area.getX() + w * (float) i, area.getY(), w, area.getHeight()).reduced (2.0f);
        if (i == index)
        {
            g.setColour (accent);
            g.fillRoundedRectangle (cell, 5.0f);
        }
        g.setColour (i == index ? juce::Colours::black : text);
        g.drawFittedText (items[i].toUpperCase(), cell.toNearestInt(), juce::Justification::centred, 1, 0.6f);
    }
}

void Segmented::mouseDown (const juce::MouseEvent& e)
{
    const int i = juce::jlimit (0, items.size() - 1, e.x * items.size() / juce::jmax (1, getWidth()));
    attachment.setValueAsCompleteGesture ((float) i);
}

// --------------------------------------------------------------------------
void PadButton::paint (juce::Graphics& g)
{
    auto area = getLocalBounds().toFloat().reduced (1.5f);
    const auto colour = padColour (pad);
    const float corner = juce::jmin (10.0f, area.getHeight() * 0.18f);

    g.setGradientFill (juce::ColourGradient (colour.withMultipliedBrightness (0.42f + 0.58f * flash), area.getX(), area.getY(),
                                             colour.withMultipliedBrightness (0.28f + 0.62f * flash), area.getX(), area.getBottom(), false));
    g.fillRoundedRectangle (area, corner);

    g.setColour (selected ? text : colour.withAlpha (0.7f));
    g.drawRoundedRectangle (area, corner, selected ? 2.2f : 1.0f);

    g.setColour (flash > 0.5f ? juce::Colours::black : text);
    g.setFont (juce::FontOptions (juce::jlimit (10.0f, 16.0f, area.getHeight() * 0.26f), juce::Font::bold));
    g.drawFittedText (juce::String (PadKeysProcessor::padName (pad)).toUpperCase(),
                      area.reduced (4.0f).toNearestInt(), juce::Justification::bottomLeft, 1, 0.6f);
}

void PadButton::mouseDown (const juce::MouseEvent& e)
{
    // Tap near the top of a pad for a hard hit, near the bottom for a soft one.
    const float height = (float) juce::jmax (1, getHeight());
    const float velocity = juce::jlimit (0.5f, 1.0f, 1.05f - 0.55f * (float) e.y / height);
    if (onHit != nullptr)
        onHit (velocity);
}

// --------------------------------------------------------------------------
namespace
{
    struct Target { const char* id; const char* name; };
    const Target targets[] = {
        { "cutoff", "Tone" }, { "reso", "Edge" }, { "fat", "Fat" }, { "attack", "Attack" }, { "release", "Release" },
        { "keysLevel", "Keys Level" }, { "fxFilter", "Sweep Filter" }, { "delayMix", "Echo" },
        { "delayFb", "Echo Repeats" }, { "swing", "Swing" }, { "tempo", "Tempo" }, { "master", "Volume" } };
}

Assignable::Assignable (PadKeysProcessor& p, int slotIndex, juce::Slider::SliderStyle style)
    : slider (style, juce::Slider::NoTextBox), processor (p), slot (slotIndex)
{
    caption.setColour (juce::TextButton::buttonColourId, panelLight);
    caption.onClick = [this] { showMenu(); };
    addAndMakeVisible (slider);
    addAndMakeVisible (caption);
    setTarget (processor.getAssignment (slot), false);
}

void Assignable::setTarget (const juce::String& paramID, bool save)
{
    target = paramID;
    attachment.reset();
    slider.getProperties().set ("fromCentre", paramID == "fxFilter");
    attachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment> (processor.apvts, paramID, slider);

    if (auto* param = processor.apvts.getParameter (paramID))
        slider.setDoubleClickReturnValue (true, param->convertFrom0to1 (param->getDefaultValue()));

    for (auto& t : targets)
        if (paramID == t.id)
            caption.setButtonText (juce::String (t.name).toUpperCase());

    if (save)
        processor.setAssignment (slot, paramID);

    slider.repaint();
}

void Assignable::showMenu()
{
    juce::PopupMenu menu;
    menu.addSectionHeader ("This control changes...");
    int id = 1;
    for (auto& t : targets)
        menu.addItem (id++, t.name, true, target == t.id);

    juce::Component::SafePointer<Assignable> safe (this);
    menu.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (&caption)
                                                  .withParentComponent (findParentComponentOfClass<juce::AudioProcessorEditor>())
                                                  .withStandardItemHeight (34),
                        [safe] (int result)
                        {
                            if (safe != nullptr && result > 0)
                                safe->setTarget (targets[result - 1].id, true);
                        });
}

void Assignable::resized()
{
    auto r = getLocalBounds();
    caption.setBounds (r.removeFromBottom (juce::jlimit (20, 30, getHeight() / 4)).reduced (2, 0));
    r.removeFromBottom (3);
    slider.setBounds (r);
}

// --------------------------------------------------------------------------
bool StepGrid::cellAt (juce::Point<int> p, int& pad, int& step) const
{
    const int lw = labelWidth();
    if (p.x < lw || p.y < 0 || p.y >= getHeight() || p.x >= getWidth())
        return false;

    const int row = juce::jlimit (0, rows - 1, p.y * rows / juce::jmax (1, getHeight()));
    step = juce::jlimit (0, PadKeysProcessor::numSteps - 1, (p.x - lw) * PadKeysProcessor::numSteps / juce::jmax (1, getWidth() - lw));
    pad = page * rows + row;
    return true;
}

void StepGrid::paint (juce::Graphics& g)
{
    const float lw = (float) labelWidth();
    const float rowH = (float) getHeight() / (float) rows;
    const float cellW = ((float) getWidth() - lw) / (float) PadKeysProcessor::numSteps;
    g.setFont (juce::FontOptions (juce::jlimit (9.0f, 14.0f, rowH * 0.45f), juce::Font::bold));

    for (int row = 0; row < rows; ++row)
    {
        const int pad = page * rows + row;
        const auto colour = padColour (pad);
        const float y = rowH * (float) row;

        auto label = juce::Rectangle<float> (0.0f, y, lw, rowH).reduced (1.5f);
        g.setColour (pad == selectedPad ? colour.withMultipliedBrightness (0.55f) : panel);
        g.fillRoundedRectangle (label, 4.0f);
        g.setColour (text);
        g.drawFittedText (juce::String (PadKeysProcessor::padName (pad)).toUpperCase(),
                          label.reduced (4.0f, 0.0f).toNearestInt(), juce::Justification::centredLeft, 1, 0.6f);

        for (int step = 0; step < PadKeysProcessor::numSteps; ++step)
        {
            auto cell = juce::Rectangle<float> (lw + cellW * (float) step, y, cellW, rowH).reduced (1.5f);
            const bool on = processor.getStep (pad, step);
            const bool beat = (step / 4) % 2 == 0;
            auto fill = on ? colour : (beat ? panelLight : panel);
            if (step == currentStep)
                fill = on ? fill.brighter (0.7f) : fill.brighter (0.25f);
            g.setColour (fill);
            g.fillRoundedRectangle (cell, 3.0f);
        }
    }
}

void StepGrid::mouseDown (const juce::MouseEvent& e)
{
    int pad = 0, step = 0;

    if (cellAt (e.getPosition(), pad, step))
    {
        paintValue = ! processor.getStep (pad, step);
        processor.setStep (pad, step, paintValue);
        repaint();
    }
    else if (e.x < labelWidth() && onPadLabel != nullptr)
    {
        onPadLabel (page * rows + juce::jlimit (0, rows - 1, e.y * rows / juce::jmax (1, getHeight())));
    }
}

void StepGrid::mouseDrag (const juce::MouseEvent& e)
{
    int pad = 0, step = 0;

    if (e.getMouseDownX() >= labelWidth() && cellAt (e.getPosition(), pad, step) && processor.getStep (pad, step) != paintValue)
    {
        processor.setStep (pad, step, paintValue);
        repaint();
    }
}
} // namespace pk

// ==========================================================================
PadKeysEditor::PadKeysEditor (PadKeysProcessor& p)
    : AudioProcessorEditor (&p), processor (p),
      modeSwitch (*p.apvts.getParameter ("mode"), { "Split", "Drums", "Keys" }),
      masterAttachment (p.apvts, "master", masterSlider),
      assignDial1 (p, 0, juce::Slider::RotaryHorizontalVerticalDrag),
      assignDial2 (p, 1, juce::Slider::RotaryHorizontalVerticalDrag),
      assignSlider (p, 2, juce::Slider::LinearVertical),
      playKeyboard (p.keyboardState, juce::MidiKeyboardComponent::horizontalKeyboard),
      grid (p),
      seqSwitch (*p.apvts.getParameter ("seqMode"), { "Off", "Song", "Free" }),
      waveSwitch (*p.apvts.getParameter ("wave"), { "Saw", "Square", "Tri", "Sine" }),
      keyboard (p.keyboardState, juce::MidiKeyboardComponent::horizontalKeyboard),
      sweepAttachment (p.apvts, "fxFilter", sweepSlider),
      echoTimeSwitch (*p.apvts.getParameter ("delayTime"), { "1/16", "1/8", "1/8 dot", "1/4" })
{
    setLookAndFeel (&look);

    title.setText ("PADKEYS", juce::dontSendNotification);
    title.setFont (juce::FontOptions (18.0f, juce::Font::bold));
    title.setColour (juce::Label::textColourId, pk::accent);
    addAndMakeVisible (title);

    styleCaption (volumeCaption, "VOL", juce::Justification::centredRight);
    addAndMakeVisible (volumeCaption);
    addAndMakeVisible (masterSlider);
    addAndMakeVisible (modeSwitch);

    static const char* const tabNames[5] = { "PLAY", "PADS", "STEPS", "KEYS", "FX" };
    for (int i = 0; i < 5; ++i)
    {
        auto& b = tabButtons[i];
        b.setButtonText (tabNames[i]);
        b.setClickingTogglesState (true);
        b.setRadioGroupId (1);
        b.onClick = [this, i] { if (tabButtons[i].getToggleState()) showTab (i); };
        addAndMakeVisible (b);
    }

    // play
    for (int i = 0; i < 8; ++i)
    {
        playPads[i].onHit = [this, i] (float velocity) { processor.hitPad (playPads[i].pad, velocity); selectPad (playPads[i].pad); };
        addChildComponent (playPads[i]);
    }
    bankButton.onClick = [this] { setPadBank (1 - padBank); };
    playKeyboard.setAvailableRange (24, 108);
    playKeyboard.setLowestVisibleKey (48);
    playKeyboard.setOctaveForMiddleC (3);
    for (auto* a : { &assignDial1, &assignDial2, &assignSlider })
        a->slider.setPopupDisplayEnabled (true, false, this);
    for (juce::Component* c : std::initializer_list<juce::Component*> { &bankButton, &assignDial1, &assignDial2, &assignSlider, &playKeyboard })
        addChildComponent (c);
    setPadBank (0);

    // pads
    for (int i = 0; i < PadKeysProcessor::numPads; ++i)
    {
        pads[i].pad = i;
        pads[i].onHit = [this, i] (float velocity) { processor.hitPad (i, velocity); selectPad (i); };
        addChildComponent (pads[i]);
    }

    padTitle.setFont (juce::FontOptions (17.0f, juce::Font::bold));
    styleCaption (levelCaption, "LEVEL");
    for (juce::Component* c : std::initializer_list<juce::Component*> { &padTitle, &levelCaption, &tuneKnob, &lengthKnob, &levelSlider })
        addChildComponent (c);

    // steps
    grid.onPadLabel = [this] (int pad) { processor.hitPad (pad, 0.85f); selectPad (pad); };
    tempoKnob.attach (p.apvts, "tempo");
    swingKnob.attach (p.apvts, "swing");
    pageButton.onClick = [this]
    {
        grid.page = 1 - grid.page;
        pageButton.setButtonText (grid.page == 0 ? "PADS 1-8" : "PADS 9-16");
        grid.repaint();
    };
    clearButton.onClick = [this] { processor.clearPattern(); grid.repaint(); };
    for (juce::Component* c : std::initializer_list<juce::Component*> { &grid, &seqSwitch, &tempoKnob, &swingKnob, &pageButton, &clearButton })
        addChildComponent (c);

    // keys
    cutoffKnob.attach (p.apvts, "cutoff");
    resoKnob.attach (p.apvts, "reso");
    attackKnob.attach (p.apvts, "attack");
    decayKnob.attach (p.apvts, "decay");
    sustainKnob.attach (p.apvts, "sustain");
    releaseKnob.attach (p.apvts, "release");
    fatKnob.attach (p.apvts, "fat");
    keysLevelKnob.attach (p.apvts, "keysLevel");
    keyboard.setAvailableRange (24, 108);
    keyboard.setLowestVisibleKey (48);
    keyboard.setOctaveForMiddleC (3);
    for (juce::Component* c : std::initializer_list<juce::Component*> { &waveSwitch, &cutoffKnob, &resoKnob, &attackKnob, &decayKnob, &sustainKnob,
                     &releaseKnob, &fatKnob, &keysLevelKnob, &keyboard })
        addChildComponent (c);

    // fx
    styleCaption (sweepCaption, "SWEEP FILTER  -  left = muffled, right = thin, double-tap to reset", juce::Justification::centredLeft);
    styleCaption (echoCaption, "ECHO TIME", juce::Justification::centredLeft);
    sweepSlider.getProperties().set ("fromCentre", true);
    sweepSlider.setDoubleClickReturnValue (true, 0.0);
    echoMixKnob.attach (p.apvts, "delayMix");
    echoRepeatKnob.attach (p.apvts, "delayFb");
    for (juce::Component* c : std::initializer_list<juce::Component*> { &sweepCaption, &echoCaption, &sweepSlider, &echoTimeSwitch, &echoMixKnob, &echoRepeatKnob })
        addChildComponent (c);

    // Show the current value in a small bubble while a dial is being turned.
    for (pk::Knob* k : { &tuneKnob, &lengthKnob, &tempoKnob, &swingKnob, &cutoffKnob, &resoKnob, &attackKnob, &decayKnob,
                         &sustainKnob, &releaseKnob, &fatKnob, &keysLevelKnob, &echoMixKnob, &echoRepeatKnob })
    {
        k->slider.setPopupDisplayEnabled (true, false, this);
        k->slider.setNumDecimalPlacesToDisplay (2);
    }

    selectPad (0);
    tabButtons[0].setToggleState (true, juce::dontSendNotification);
    showTab (0);

    setResizable (true, true);
    setResizeLimits (420, 200, 2400, 1600);
    setSize (940, 440);
    startTimerHz (30);
}

PadKeysEditor::~PadKeysEditor()
{
    stopTimer();
    setLookAndFeel (nullptr);
}

void PadKeysEditor::styleCaption (juce::Label& label, const juce::String& textToShow, juce::Justification just)
{
    label.setText (textToShow, juce::dontSendNotification);
    label.setJustificationType (just);
    label.setFont (juce::FontOptions (12.0f, juce::Font::bold));
    label.setColour (juce::Label::textColourId, pk::dim);
    label.setMinimumHorizontalScale (0.5f);
}

void PadKeysEditor::selectPad (int pad)
{
    selectedPad = pad;
    padTitle.setText (juce::String (PadKeysProcessor::padName (pad)).toUpperCase(), juce::dontSendNotification);
    padTitle.setColour (juce::Label::textColourId, pk::padColour (pad));

    tuneKnob.attach (processor.apvts, "tune" + juce::String (pad));
    lengthKnob.attach (processor.apvts, "decay" + juce::String (pad));
    levelAttachment.reset();
    levelAttachment = std::make_unique<SliderAttachment> (processor.apvts, "level" + juce::String (pad), levelSlider);

    for (int i = 0; i < PadKeysProcessor::numPads; ++i)
    {
        pads[i].selected = i == pad;
        pads[i].repaint();
    }

    for (auto& pp : playPads)
    {
        pp.selected = pp.pad == pad;
        pp.repaint();
    }

    grid.selectedPad = pad;
    grid.repaint();
}

std::vector<juce::Component*> PadKeysEditor::tabComponents (int tab)
{
    std::vector<juce::Component*> c;

    switch (tab)
    {
        case 0:
            for (auto& pad : playPads) c.push_back (&pad);
            c.insert (c.end(), { &bankButton, &assignDial1, &assignDial2, &assignSlider, &playKeyboard });
            break;
        case 1:
            for (auto& pad : pads) c.push_back (&pad);
            c.insert (c.end(), { &padTitle, &levelCaption, &tuneKnob, &lengthKnob, &levelSlider });
            break;
        case 2:
            c = { &grid, &seqSwitch, &tempoKnob, &swingKnob, &pageButton, &clearButton };
            break;
        case 3:
            c = { &waveSwitch, &cutoffKnob, &resoKnob, &attackKnob, &decayKnob, &sustainKnob,
                  &releaseKnob, &fatKnob, &keysLevelKnob, &keyboard };
            break;
        default:
            c = { &sweepCaption, &echoCaption, &sweepSlider, &echoTimeSwitch, &echoMixKnob, &echoRepeatKnob };
            break;
    }

    return c;
}

void PadKeysEditor::showTab (int tab)
{
    currentTab = tab;
    tabButtons[tab].setToggleState (true, juce::dontSendNotification);

    for (int t = 0; t < 5; ++t)
        for (auto* c : tabComponents (t))
            c->setVisible (t == tab);
}

void PadKeysEditor::setPadBank (int bank)
{
    padBank = bank;
    bankButton.setButtonText (bank == 0 ? "PADS 1-8" : "PADS 9-16");

    for (int i = 0; i < 8; ++i)
    {
        playPads[i].pad = bank * 8 + i;
        playPads[i].selected = playPads[i].pad == selectedPad;
        playPads[i].repaint();
    }
}

void PadKeysEditor::timerCallback()
{
    for (int i = 0; i < PadKeysProcessor::numPads; ++i)
    {
        const auto hits = processor.hitCount[(size_t) i].load();
        auto& pad = pads[i];

        if (hits != lastHit[(size_t) i])
        {
            lastHit[(size_t) i] = hits;
            pad.flash = 1.0f;
            pad.repaint();
        }
        else if (pad.flash > 0.0f)
        {
            pad.flash = pad.flash < 0.05f ? 0.0f : pad.flash * 0.72f;
            pad.repaint();
        }
    }

    for (auto& pp : playPads)
    {
        const float f = pads[pp.pad].flash;
        if (! juce::approximatelyEqual (f, pp.flash))
        {
            pp.flash = f;
            pp.repaint();
        }
    }

    const int step = processor.currentStep.load();
    if (step != grid.currentStep)
    {
        grid.currentStep = step;
        if (currentTab == 2)
            grid.repaint();
    }
}

void PadKeysEditor::paint (juce::Graphics& g)
{
    g.fillAll (pk::background);
}

void PadKeysEditor::resized()
{
    const int gap = 6;
    auto area = getLocalBounds().reduced (gap);
    const int barH = juce::jlimit (30, 44, getHeight() / 8);
    auto bar = area.removeFromTop (barH);
    area.removeFromTop (gap);

    // ---- top bar ----
    const bool wide = getWidth() >= 760;
    title.setVisible (wide);
    if (wide)
        title.setBounds (bar.removeFromLeft (104));

    const int tabW = juce::jlimit (46, 78, getWidth() / 13);
    for (auto& b : tabButtons)
        b.setBounds (bar.removeFromLeft (tabW).reduced (2, 1));

    masterSlider.setBounds (bar.removeFromRight (juce::jlimit (70, 170, getWidth() / 6)));
    volumeCaption.setBounds (bar.removeFromRight (34));
    bar.removeFromLeft (gap);
    modeSwitch.setBounds (bar.withSizeKeepingCentre (juce::jmin (bar.getWidth(), 220), barH - 4));

    // ---- play: pads over keyboard, assignable controls on the right ----
    {
        auto b = area;
        auto keys = b.removeFromBottom (juce::jlimit (56, 220, b.getHeight() * 44 / 100));
        playKeyboard.setBounds (keys);
        playKeyboard.setKeyWidth (juce::jlimit (26.0f, 64.0f, (float) keys.getWidth() / 15.0f));
        b.removeFromBottom (gap);

        auto side = b.removeFromRight (juce::jlimit (190, 360, b.getWidth() * 36 / 100));
        b.removeFromRight (gap);
        assignSlider.setBounds (side.removeFromRight (juce::jlimit (56, 90, side.getWidth() / 4)));
        side.removeFromRight (gap);
        assignDial1.setBounds (side.removeFromLeft (side.getWidth() / 2).reduced (2, 0));
        assignDial2.setBounds (side.reduced (2, 0));

        bankButton.setBounds (b.removeFromLeft (juce::jlimit (44, 64, b.getWidth() / 10)).reduced (0, 2));
        b.removeFromLeft (2);
        const float cw = (float) b.getWidth() / 4.0f, ch = (float) b.getHeight() / 2.0f;
        for (int i = 0; i < 8; ++i)
            playPads[i].setBounds (juce::Rectangle<float> ((float) b.getX() + cw * (float) (i % 4),
                                                           (float) b.getY() + ch * (float) (1 - i / 4), cw, ch).toNearestInt().reduced (2));
    }

    // ---- pads ----
    {
        auto b = area;
        auto side = b.removeFromRight (juce::jlimit (150, 320, b.getWidth() * 32 / 100));
        b.removeFromRight (gap);

        const float cw = (float) b.getWidth() / 4.0f, ch = (float) b.getHeight() / 4.0f;
        for (int i = 0; i < PadKeysProcessor::numPads; ++i)
            pads[i].setBounds (juce::Rectangle<float> ((float) b.getX() + cw * (float) (i % 4),
                                                       (float) b.getY() + ch * (float) (3 - i / 4), cw, ch).toNearestInt().reduced (2));

        padTitle.setBounds (side.removeFromTop (juce::jlimit (20, 28, side.getHeight() / 8)));
        auto levelArea = side.removeFromRight (juce::jlimit (44, 70, side.getWidth() / 4));
        levelCaption.setBounds (levelArea.removeFromBottom (16));
        levelSlider.setBounds (levelArea);

        if (side.getWidth() >= side.getHeight())
        {
            tuneKnob.setBounds (side.removeFromLeft (side.getWidth() / 2).reduced (2));
            lengthKnob.setBounds (side.reduced (2));
        }
        else
        {
            tuneKnob.setBounds (side.removeFromTop (side.getHeight() / 2).reduced (2));
            lengthKnob.setBounds (side.reduced (2));
        }
    }

    // ---- steps ----
    {
        auto b = area;
        auto side = b.removeFromRight (juce::jlimit (130, 220, b.getWidth() / 4));
        b.removeFromRight (gap);
        grid.setBounds (b);

        const int rowH = juce::jlimit (26, 36, side.getHeight() / 6);
        seqSwitch.setBounds (side.removeFromTop (rowH));
        auto buttons = side.removeFromBottom (rowH);
        pageButton.setBounds (buttons.removeFromLeft (buttons.getWidth() * 3 / 5).reduced (1));
        clearButton.setBounds (buttons.reduced (1));
        side.reduce (0, 4);
        tempoKnob.setBounds (side.removeFromLeft (side.getWidth() / 2));
        swingKnob.setBounds (side);
    }

    // ---- keys ----
    {
        auto b = area;
        auto keys = b.removeFromBottom (juce::jlimit (56, 190, b.getHeight() * 45 / 100));
        keyboard.setBounds (keys);
        keyboard.setKeyWidth (juce::jlimit (26.0f, 64.0f, (float) keys.getWidth() / 15.0f));
        b.removeFromBottom (gap);

        auto waveArea = b.removeFromLeft (juce::jlimit (150, 250, b.getWidth() / 4));
        waveSwitch.setBounds (waveArea.withSizeKeepingCentre (waveArea.getWidth(), juce::jmin (36, waveArea.getHeight())));
        b.removeFromLeft (gap);

        pk::Knob* knobs[] = { &cutoffKnob, &resoKnob, &attackKnob, &decayKnob, &sustainKnob, &releaseKnob, &fatKnob, &keysLevelKnob };
        const float kw = (float) b.getWidth() / 8.0f;
        for (int i = 0; i < 8; ++i)
            knobs[i]->setBounds (juce::Rectangle<float> ((float) b.getX() + kw * (float) i, (float) b.getY(), kw, (float) b.getHeight()).toNearestInt());
    }

    // ---- fx ----
    {
        auto b = area.reduced (gap, 0);
        auto top = b.removeFromTop (b.getHeight() / 2);
        sweepCaption.setBounds (top.removeFromTop (18));
        sweepSlider.setBounds (top.reduced (0, 4));

        b.removeFromTop (gap);
        auto knobsArea = b.removeFromRight (juce::jlimit (160, 340, b.getWidth() * 2 / 5));
        echoMixKnob.setBounds (knobsArea.removeFromLeft (knobsArea.getWidth() / 2));
        echoRepeatKnob.setBounds (knobsArea);
        b.removeFromRight (gap * 2);
        echoCaption.setBounds (b.removeFromTop (18));
        echoTimeSwitch.setBounds (b.withSizeKeepingCentre (b.getWidth(), juce::jmin (40, b.getHeight())));
    }
}
