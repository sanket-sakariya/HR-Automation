/**
 * Audio Capture Worklet Processor
 * 
 * Captures audio from microphone in real-time and converts to 16-bit PCM.
 * Runs in a separate audio thread for low-latency, click-free operation.
 * 
 * Input: Float32 audio samples from microphone
 * Output: Int16 PCM chunks + audio levels for visualization
 */

class CaptureProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
        
        // Configuration
        this.chunkSize = options.processorOptions?.chunkSize || 2048;
        
        // Buffer for accumulating samples
        this.buffer = new Float32Array(this.chunkSize);
        this.bufferIndex = 0;
        
        // For level metering
        this.levelBins = 40;
        this.levelBuffer = new Float32Array(this.levelBins);
        this.levelIndex = 0;
    }
    
    /**
     * Process audio - called every ~2.9ms (128 samples at 44.1kHz)
     * We need to resample and accumulate to get proper 16kHz chunks
     */
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        if (!input || !input[0]) {
            return true; // Keep processor alive
        }
        
        const samples = input[0]; // Mono channel
        
        // Accumulate samples
        for (let i = 0; i < samples.length; i++) {
            const sample = samples[i];
            
            // Store sample
            if (this.bufferIndex < this.chunkSize) {
                this.buffer[this.bufferIndex] = sample;
                this.bufferIndex++;
            }
            
            // Calculate level for visualization
            const absValue = Math.abs(sample);
            this.levelBuffer[this.levelIndex] = Math.max(
                this.levelBuffer[this.levelIndex],
                absValue
            );
        }
        
        // Update level bin index
        this.levelIndex = (this.levelIndex + 1) % this.levelBins;
        
        // When buffer is full, send chunk
        if (this.bufferIndex >= this.chunkSize) {
            // Convert Float32 to Int16 PCM
            const pcmData = this.float32ToInt16(this.buffer);
            
            // Get levels for visualization
            const levels = Array.from(this.levelBuffer);
            
            // Send to main thread
            this.port.postMessage({
                pcmData: pcmData.buffer,
                levels: levels
            }, [pcmData.buffer]); // Transfer ownership for performance
            
            // Reset buffers
            this.buffer = new Float32Array(this.chunkSize);
            this.bufferIndex = 0;
            this.levelBuffer.fill(0);
        }
        
        return true; // Keep processor alive
    }
    
    /**
     * Convert Float32 [-1.0, 1.0] to Int16 [-32768, 32767]
     */
    float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        
        for (let i = 0; i < float32Array.length; i++) {
            // Clamp to [-1, 1]
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            // Convert to Int16
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        return int16Array;
    }
}

// Register the processor
registerProcessor('capture-processor', CaptureProcessor);
