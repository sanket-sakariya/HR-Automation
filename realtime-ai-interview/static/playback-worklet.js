/**
 * Audio Playback Worklet Processor
 * 
 * Smooth, click-free audio playback using a ring buffer.
 * This is CRITICAL for natural-sounding voice output.
 * 
 * Features:
 * - Ring buffer to handle network jitter
 * - Smooth start/stop to prevent clicks
 * - Level metering for visualization
 * - Immediate clear for barge-in support
 * 
 * Input: Float32 audio samples from Gemini (via postMessage)
 * Output: Smooth audio playback to speakers
 */

class PlaybackProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        
        // Ring buffer configuration
        // 24kHz * 2 seconds = 48000 samples buffer
        this.bufferSize = 48000;
        this.buffer = new Float32Array(this.bufferSize);
        this.writeIndex = 0;
        this.readIndex = 0;
        this.samplesAvailable = 0;
        
        // Smoothing to prevent clicks
        this.fadeLength = 128; // Samples for fade in/out
        this.isPlaying = false;
        this.fadeGain = 0;
        
        // For visualization
        this.levelBins = 40;
        this.levelBuffer = new Float32Array(this.levelBins);
        this.levelIndex = 0;
        this.levelCounter = 0;
        this.levelInterval = 64; // Update levels more frequently (every 64 samples ~2.7ms)
        
        // Handle messages from main thread
        this.port.onmessage = (event) => {
            this.handleMessage(event.data);
        };
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'audio':
                this.enqueueAudio(data.samples);
                break;
                
            case 'clear':
                this.clearBuffer();
                break;
        }
    }
    
    /**
     * Add audio samples to the ring buffer
     */
    enqueueAudio(samples) {
        for (let i = 0; i < samples.length; i++) {
            // Write to ring buffer
            this.buffer[this.writeIndex] = samples[i];
            this.writeIndex = (this.writeIndex + 1) % this.bufferSize;
            
            // Track available samples (don't exceed buffer size)
            if (this.samplesAvailable < this.bufferSize) {
                this.samplesAvailable++;
            } else {
                // Buffer overflow - move read index (drop oldest samples)
                this.readIndex = (this.readIndex + 1) % this.bufferSize;
            }
        }
        
        // Start playing if we have enough buffered (100ms at 24kHz = 2400 samples)
        if (!this.isPlaying && this.samplesAvailable > 2400) {
            this.isPlaying = true;
        }
    }
    
    /**
     * Clear buffer immediately (for barge-in)
     */
    clearBuffer() {
        this.buffer.fill(0);
        this.writeIndex = 0;
        this.readIndex = 0;
        this.samplesAvailable = 0;
        this.isPlaying = false;
        this.fadeGain = 0;
        this.levelBuffer.fill(0);
    }
    
    /**
     * Process audio - called every ~2.9ms (128 samples at 24kHz)
     */
    process(inputs, outputs, parameters) {
        const output = outputs[0];
        
        if (!output || !output[0]) {
            return true;
        }
        
        const outputChannel = output[0];
        let maxLevel = 0;
        
        for (let i = 0; i < outputChannel.length; i++) {
            let sample = 0;
            
            if (this.isPlaying && this.samplesAvailable > 0) {
                // Read from ring buffer
                sample = this.buffer[this.readIndex];
                this.readIndex = (this.readIndex + 1) % this.bufferSize;
                this.samplesAvailable--;
                
                // Fade in to prevent click at start
                if (this.fadeGain < 1) {
                    this.fadeGain = Math.min(1, this.fadeGain + (1 / this.fadeLength));
                }
                sample *= this.fadeGain;
                
            } else if (this.fadeGain > 0) {
                // Fade out when buffer empties to prevent click
                this.fadeGain = Math.max(0, this.fadeGain - (1 / this.fadeLength));
                sample = 0;
                
                if (this.fadeGain === 0) {
                    this.isPlaying = false;
                }
            }
            
            outputChannel[i] = sample;
            
            // Track level for visualization
            maxLevel = Math.max(maxLevel, Math.abs(sample));
        }
        
        // Update visualization levels - send on every cycle when playing
        this.levelBuffer[this.levelIndex] = maxLevel;
        this.levelIndex = (this.levelIndex + 1) % this.levelBins;
        
        // Send levels to main thread for visualization
        if (this.isPlaying || this.fadeGain > 0) {
            this.port.postMessage({
                type: 'levels',
                levels: Array.from(this.levelBuffer),
                isPlaying: this.isPlaying,
                maxLevel: maxLevel
            });
        }
        
        return true; // Keep processor alive
    }
}

// Register the processor
registerProcessor('playback-processor', PlaybackProcessor);
