# pa2ohh-dsc-hfsnoop
[Reception of DSC (Digital Selective Calling) on MF/HF](https://www.qsl.net/pa2ohh/23hfdsc.htm) orginally developed by PA2OHH.

A PDF snapshot of his site can be viewed [pa2ohh_23hfdsc_(RECEPTION_OF_DIGITAL_SELECTIVE_CALLING_ON_MF-HF).pdf](./doc/pa2ohh_23hfdsc_(RECEPTION_OF_DIGITAL_SELECTIVE_CALLING_ON_MF-HF).pdf).

# Install Dependencies

```
cd pa2ohh-dsc-hfsnoop
python3 -m venv env
source ./env/bin/activate

pip install tk pyaudio numpy
```

# Running via UI

The Commands syntax / options are:

```
$ python DSCHFsnoop.py -h
usage: DSCHFsnoop.py [-h] [-as {alsa,-}] [-sr {11025,22050,44100}] [-dd DATA_DIR] freq_hz

MF-HF-DSC Decoder

positional arguments:
  freq_hz               Frequency (Hz) which feed is streaming from.

options:
  -h, --help            show this help message and exit
  -as {alsa,-}, --audio-src {alsa,-}
                        Source for audio feed. Expected s16be format for raw / STDIN feed.
  -sr {11025,22050,44100}, --sig-rate {11025,22050,44100}
                        Audio sample.
  -dd DATA_DIR, --data-dir DATA_DIR
                        Root level for data files.
```

You need to at minimum specify the **frequency** in Hz. Is is require to ensure when we are running multiple instance we can tell which window is which.  The value for frequency can be any number its currently not being validated.

```
python DSCHFsnoop.py 8414500
```
# Audio Source Enhancement

The original tool was 100% UI Driven and the user could only select from the set of sound cards (or virtual card if configured) via the UI to specify where you wanted your audio stream from.  For my needs with [KA9Q-Radio](https://github.com/ka9q/ka9q-radio) I needed the application to have means to to allow me to pipe raw audio data in to it. With the exsiting KA9Q-Radio tool '**pcmrecord**' I can stream the auto data for all the DSC channel via STDIN.  So at this time the bulk of the work has been done to enabled this including some refactoring of the existing Audio logic to allow easy switch between sources.

## Using KA9Q-Radio PCMRECORD 

For KA9Q-Radio I run the following commands to monitor all 6 DSC channels via my RX888-mk2 SDR:

```
pcmrecord -c -r -f -S 2185 gmdss-pcm.local | python DSCHFsnoop.py 2187500 -as -
pcmrecord -c -r -f -S 4206 gmdss-pcm.local | python DSCHFsnoop.py 4207400 -as -
pcmrecord -c -r -f -S 6310 gmdss-pcm.local | python DSCHFsnoop.py 6312000 -as -
pcmrecord -c -r -f -S 8413 gmdss-pcm.local | python DSCHFsnoop.py 8414500 -as -
pcmrecord -c -r -f -S 12575 gmdss-pcm.local | python DSCHFsnoop.py 12577000 -as -
pcmrecord -c -r -f -S 16803 gmdss-pcm.local | python DSCHFsnoop.py 16804500 -as -
```

## Using Sox

If you don't have an SDR or Radio, then good news!! for testing purpuse you can use the likes of 'sox' to pipe a wav/mp3 audio file int for testing.  

Download the examples from [SigID Wiki - GMDSS Digital Selective Calling](https://www.sigidwiki.com/wiki/GMDSS_Digital_Selective_Calling)

```
wget -O /tmp/Dsc_examples.mp3 https://www.sigidwiki.com/images/c/cb/Dsc_examples.mp3
wget -O /tmp/GMDSS_1.mp3 https://www.sigidwiki.com/images/e/e1/GMDSS_1.mp3
wget -O /tmp/GMDSS_2.mp3 https://www.sigidwiki.com/images/f/f8/GMDSS_2.mp3
wget -O /tmp/GMDSS_3.mp3 https://www.sigidwiki.com/images/7/7c/GMDSS_3.mp3
```

### Example 1:
```
sox /tmp/Dsc_examples.mp3 -t raw -r 44100 -b 16 -c 1 - |  python DSCHFsnoop.py 9999999 -as - -sr 44100

===================================
[20251107-07:05:59] 
FMS-120: Selective individual call
ADRS-ID: 002320001 COAST CC232 [United Kingdom of Great Britain and Northern Ireland]
CAT-100: Routine
SELF-ID: 005030001 COAST CC503 [Australia]
INFO-DB: [RCC Australia 26.20S 120.33E]
TC1-109: J3E TP
TC2-126: No Availability information
FREQ-RX: 8291.0 kHz
FREQ-TX: 8291.0 kHz
EOS-117: Acknowledgement required
===================================
[20251107-07:06:03] 
FMS-120: Selective individual call
ADRS-ID: 005030001 COAST CC503 [Australia]
CAT-100: Routine
SELF-ID: 002320001 COAST CC232 [United Kingdom of Great Britain and Northern Ireland]
INFO-DB: [Shetland Coastguard 60.32N 001.23W]
TC1-109: J3E TP
TC2-126: No Availability information
FREQ-RX: 8291.0 kHz
FREQ-TX: 8291.0 kHz
EOS-122: Acknowledgement given

```

### Example 2:

```
sox /tmp/GMDSS_1.mp3 -t raw -r 44100 -b 16 -c 1 - |  python DSCHFsnoop.py 9999999 -as - -sr 44100

===================================
[20251107-07:07:13] 
FMS-120: Selective individual call
ADRS-ID: 004634060 COAST CC463 [Pakistan (Islamic Republic of)]
CAT-108: Safety
SELF-ID: 215322000 INDIVIDUAL CC215 [Malta]
TC1-118: Test
TC2-126: No Availability information
FREQ-RX: NONE
FREQ-TX: NONE
EOS-117: Acknowledgement required
```

### Example 3:

While investigating why the SigID Wiki GMDSS_2.mp3 example failed to decode, I identified it's tones were reversed (ie possibly recorded using LSB instead of USB). 

```
sox /tmp/GMDSS_2.mp3 -t raw -r 44100 -b 16 -c 1 - |  python DSCHFsnoop.py 9999999 -as - -sr 44100 --inv

===================================
FMS-120: Selective individual call
ADRS-ID: 230145000 INDIVIDUAL CC230 [Finland]
CAT-108: Safety
SELF-ID: 002191000 COAST CC219 [Denmark]
SELF-ID: Unknown Coast station: 002191000
TC1-118: Test
TC2-126: No Availability information
FREQ-RX: NONE
FREQ-TX: NONE
EOS-122: Acknowledgement given
```

### Example 4:

```
sox /tmp/GMDSS_3.mp3 -t raw -r 44100 -b 16 -c 1 - |  python DSCHFsnoop.py 9999999 -as - -sr 44100

===================================
[20251107-07:10:58] 
FMS-120: Selective individual call
ADRS-ID: 312724000 INDIVIDUAL CC312 [Belize]
CAT-108: Safety
SELF-ID: 312714000 INDIVIDUAL CC312 [Belize]
TC1-109: J3E TP
TC2-126: No Availability information
FREQ-RX: 12360.0 kHz
FREQ-TX: 12360.0 kHz
EOS-117: Acknowledgement required
```

# Updating the YADD MMSI Coast and Ship Data files

Run the following shell script:

```
./download_latest_yadd_mmsi_files.sh
```
