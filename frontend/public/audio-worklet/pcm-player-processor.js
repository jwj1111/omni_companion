class PcmPlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.capacity = Math.max(24000, Math.ceil(sampleRate * 20))
    this.buffer = new Float32Array(this.capacity)
    this.readIndex = 0
    this.writeIndex = 0
    this.available = 0
    this.started = false
    this.prebufferFrames = Math.ceil(sampleRate * 0.32)

    this.port.onmessage = (event) => {
      const message = event.data || {}
      if (message.type === 'config') {
        this.prebufferFrames = Math.max(0, Math.min(message.prebufferFrames || this.prebufferFrames, this.capacity - 1))
      } else if (message.type === 'audio' && message.samples) {
        this.append(new Float32Array(message.samples))
      } else if (message.type === 'flush') {
        this.reset()
      }
    }
  }

  reset() {
    this.readIndex = 0
    this.writeIndex = 0
    this.available = 0
    this.started = false
  }

  append(samples) {
    for (let i = 0; i < samples.length; i++) {
      if (this.available >= this.capacity) {
        this.readIndex = (this.readIndex + 1) % this.capacity
        this.available--
      }
      this.buffer[this.writeIndex] = samples[i]
      this.writeIndex = (this.writeIndex + 1) % this.capacity
      this.available++
    }
  }

  readSample() {
    if (this.available <= 0) return 0
    const sample = this.buffer[this.readIndex]
    this.readIndex = (this.readIndex + 1) % this.capacity
    this.available--
    return sample
  }

  process(inputs, outputs) {
    const output = outputs[0]
    if (!output || output.length === 0) return true

    const firstChannel = output[0]

    if (!this.started) {
      if (this.available >= this.prebufferFrames) {
        this.started = true
      } else {
        firstChannel.fill(0)
        for (let channel = 1; channel < output.length; channel++) {
          output[channel].set(firstChannel)
        }
        return true
      }
    }

    for (let i = 0; i < firstChannel.length; i++) {
      if (this.available <= 0) {
        this.started = false
        firstChannel[i] = 0
      } else {
        firstChannel[i] = this.readSample()
      }
    }

    for (let channel = 1; channel < output.length; channel++) {
      output[channel].set(firstChannel)
    }

    return true
  }
}

registerProcessor('pcm-player-processor', PcmPlayerProcessor)
