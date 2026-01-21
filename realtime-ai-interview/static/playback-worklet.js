/**
 * Audio Playback Worklet Processor (Legacy - Not Used)
 * 
 * This file is kept for compatibility but the main playback
 * now uses a simpler queue-based approach in app.js
 */

class PlaybackProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.port.onmessage = () => {};
    }
    
    process(inputs, outputs, parameters) {
        return true;
    }
}

registerProcessor('playback-processor', PlaybackProcessor);
