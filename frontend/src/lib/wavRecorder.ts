/** Emit independent PCM WAV chunks; MediaRecorder's WebM fragments are not WAV files. */
export class WavRecorder {
  state: "inactive" | "recording" = "inactive";
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  private context: AudioContext;
  private source: MediaStreamAudioSourceNode;
  private processor: ScriptProcessorNode;
  private gain: GainNode;
  private chunks: Float32Array[] = [];
  private samples = 0;
  private target = 0;
  constructor(stream: MediaStream) {
    this.context = new AudioContext();
    this.source = this.context.createMediaStreamSource(stream);
    // ScriptProcessor keeps this college prototype compatible without an external worklet asset.
    this.processor = this.context.createScriptProcessor(4096, 1, 1);
    this.gain = this.context.createGain();
    this.gain.gain.value = 0;
  }
  start(milliseconds = 4000) {
    this.target = Math.round(this.context.sampleRate * milliseconds / 1000);
    this.state = "recording";
    this.processor.onaudioprocess = (event) => {
      if (this.state !== "recording") return;
      const data = event.inputBuffer.getChannelData(0);
      let offset = 0;
      while (offset < data.length) {
        const count = Math.min(this.target - this.samples, data.length - offset);
        this.chunks.push(data.slice(offset, offset + count));
        this.samples += count; offset += count;
        if (this.samples === this.target) this.emit();
      }
    };
    this.source.connect(this.processor); this.processor.connect(this.gain); this.gain.connect(this.context.destination);
    void this.context.resume();
  }
  private emit() {
    const wav = new ArrayBuffer(44 + this.samples * 2);
    const view = new DataView(wav);
    const ascii = (offset: number, text: string) => { for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i)); };
    ascii(0, "RIFF"); view.setUint32(4, 36 + this.samples * 2, true); ascii(8, "WAVE"); ascii(12, "fmt ");
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, this.context.sampleRate, true); view.setUint32(28, this.context.sampleRate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true); ascii(36, "data"); view.setUint32(40, this.samples * 2, true);
    let offset = 44;
    for (const chunk of this.chunks) for (let i = 0; i < chunk.length; i++) { const s = Math.max(-1, Math.min(1, chunk[i])); view.setInt16(offset, s < 0 ? s * 32768 : s * 32767, true); offset += 2; }
    this.chunks = []; this.samples = 0;
    this.ondataavailable?.({ data: new Blob([wav], { type: "audio/wav" }) });
  }
  stop() {
    this.state = "inactive"; this.processor.onaudioprocess = null;
    this.source.disconnect(); this.processor.disconnect(); this.gain.disconnect();
    this.chunks = []; this.samples = 0;
    void this.context.close();
  }
}
