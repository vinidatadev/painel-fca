/**
 * Gera arquivos WAV de notificação em public/sounds/
 * Executado no build: node scripts/gen-sounds.js
 */
const fs = require('fs')
const path = require('path')

const OUT_DIR = path.join(__dirname, '..', 'public', 'sounds')
fs.mkdirSync(OUT_DIR, { recursive: true })

const SAMPLE_RATE = 22050

function makeWav(notes) {
  const totalMs = notes.reduce((m, n) => Math.max(m, n.start_ms + n.dur_ms), 0) + 80
  const numSamples = Math.ceil(SAMPLE_RATE * totalMs / 1000)
  const buf = new Int16Array(numSamples)

  for (const { freq, start_ms, dur_ms, vol = 0.45 } of notes) {
    const s0 = Math.floor(SAMPLE_RATE * start_ms / 1000)
    const sN = Math.floor(SAMPLE_RATE * (start_ms + dur_ms) / 1000)
    for (let i = s0; i < sN && i < numSamples; i++) {
      const t = (i - s0) / SAMPLE_RATE
      const attack = Math.min(1, t / 0.008)
      const release = Math.min(1, (sN - i) / (SAMPLE_RATE * 0.04))
      const env = attack * release
      buf[i] = Math.max(-32768, Math.min(32767,
        buf[i] + Math.round(32767 * vol * env * Math.sin(2 * Math.PI * freq * t))
      ))
    }
  }

  const dataLen = buf.byteLength
  const header = Buffer.alloc(44)
  header.write('RIFF', 0)
  header.writeUInt32LE(36 + dataLen, 4)
  header.write('WAVE', 8)
  header.write('fmt ', 12)
  header.writeUInt32LE(16, 16)        // chunk size
  header.writeUInt16LE(1, 20)         // PCM
  header.writeUInt16LE(1, 22)         // mono
  header.writeUInt32LE(SAMPLE_RATE, 24)
  header.writeUInt32LE(SAMPLE_RATE * 2, 28)
  header.writeUInt16LE(2, 32)         // block align
  header.writeUInt16LE(16, 34)        // bits per sample
  header.write('data', 36)
  header.writeUInt32LE(dataLen, 40)

  return Buffer.concat([header, Buffer.from(buf.buffer)])
}

const SOUNDS = {
  // som1: dois bipes suaves — estilo WhatsApp
  'som1.wav': makeWav([
    { freq: 880,  start_ms: 0,   dur_ms: 130 },
    { freq: 1100, start_ms: 160, dur_ms: 130 },
  ]),
  // som2: tom crescente — estilo Telegram
  'som2.wav': makeWav([
    { freq: 660,  start_ms: 0,   dur_ms: 90  },
    { freq: 880,  start_ms: 110, dur_ms: 90  },
    { freq: 1100, start_ms: 220, dur_ms: 130 },
  ]),
  // som3: sino suave
  'som3.wav': makeWav([
    { freq: 1047, start_ms: 0, dur_ms: 600, vol: 0.5 },
    { freq: 1319, start_ms: 0, dur_ms: 350, vol: 0.2 },
  ]),
  // som4: pulso duplo urgente
  'som4.wav': makeWav([
    { freq: 520, start_ms: 0,   dur_ms: 160, vol: 0.5 },
    { freq: 520, start_ms: 220, dur_ms: 160, vol: 0.5 },
  ]),
}

for (const [name, data] of Object.entries(SOUNDS)) {
  const file = path.join(OUT_DIR, name)
  fs.writeFileSync(file, data)
  console.log(`Gerado: ${file} (${data.length} bytes)`)
}

console.log('Sons gerados com sucesso.')
