import sounddevice as sd
import numpy as np
import time

# =========================================================
# --- DETECTOR DE APLAUSOS ---
# Escucha el micrófono en tiempo real y detecta picos de audio
# que coincidan con el patrón de un aplauso.
# PARA APRENDER: el algoritmo se basa en analizar el volumen (RMS) del audio
# y detectar subidas súbitas (spikes) que superen un umbral dinámico
# adaptado al ruido ambiental. También implementa un cooldown para evitar
# =========================================================

class ClapDetector:
    def __init__(self, sens, cooldown, on_clap, device=None):
        # sens: sensibilidad del detector (0.0 a 1.0)
        #   - valores bajos → necesita más volumen para detectar
        #   - valores altos → detecta con menos volumen (más falsos positivos)
        self.sens = sens

        # cooldown: segundos mínimos entre detecciones consecutivas
        # evita que un solo aplauso dispare múltiples eventos
        self.cooldown = cooldown

        # función que se llama cuando se detecta un aplauso 
        self.on_clap = on_clap

        # selección de dispositivo de audio 
        self.device   = device  # None = dispositivo por defecto del sistema

        # timestamp del último aplauso detectado (para calcular cooldown)
        self.last_trigger = 0

        # estado del stream de audio
        self.running = False
        self.stream  = None

        # rms del frame anterior (para calcular el delta/spike)
        self.prev_rms = 0

        # nivel de ruido ambiental estimado dinámicamente
        # se actualiza en cada frame para adaptarse al ambiente
        # valor inicial bajo para no bloquear detecciones al arrancar
        self.noise_floor = 0.01
        
        # Cuando True, usa 0.3s de cooldown en vez del normal
        # Se activa mientras logic espera un posible segundo aplauso
        self.use_short_cooldown = False

    def callback(self, indata, frames, time_info, status):
        # Este método se llama automáticamente por sounddevice
        # cada vez que hay un nuevo bloque de audio disponible

        if not self.running:
            return

        now   = time.time()
        audio = indata[:, 0]  # canal mono (primer canal)

        # RMS: nivel de volumen del frame actual
        # Root Mean Square → representa la energía del audio
        rms = np.sqrt(np.mean(audio**2))

        # Actualiza el ruido ambiental con una media exponencial
        # 0.995 → peso del pasado, 0.005 → peso del frame actual
        # Esto hace que el ruido_floor suba/baje muy lentamente
        if rms < self.noise_floor * 3:
            self.noise_floor = max(
                0.003,
                0.995 * self.noise_floor + 0.005 * rms
            )

        # Delta: diferencia entre el volumen actual y el anterior
        # Un valor alto indica un pico súbito → posible aplauso
        delta = rms - self.prev_rms
        self.prev_rms = rms

        # Condición 1: el volumen supera un mínimo absoluto
        # Evita falsos positivos en silencio total
        absolute_threshold = max(0.02, self.noise_floor * 2)
        is_loud_absolute = rms > absolute_threshold

        # Condición 2: sensibilidad dinámica
        # Valores bajos = extremadamente difícil detectar
        # Valores altos = extremadamente fácil detectar

        # Normaliza sens de 0.0-2.0 → 0.0-1.0
        normalized = self.sens / 2.0

        # Curva exponencial agresiva
        threshold = 1 + ((1 - normalized) ** 3) * 30

        is_loud_relative = rms > self.noise_floor * threshold

        # Condición 3: el pico fue súbito (spike)
        # Un aplauso sube rápido, no gradualmente
        spike_threshold = max(0.01, self.noise_floor * 3)
        is_spike = delta > spike_threshold

        # Condición 4: el evento fue corto
        # Un aplauso cae rápido después del pico
        short_event = rms < self.prev_rms * 1.2

        # Usa cooldown corto si estamos esperando un posible doble aplauso
        effective_cooldown = 0.3 if self.use_short_cooldown else self.cooldown

        if (
            is_loud_absolute
            and is_loud_relative
            and is_spike
            and short_event
            and (now - self.last_trigger > effective_cooldown)
        ):
            self.last_trigger = now
            self.on_clap()
        
        
    def start(self):
        # Inicia el stream de audio para comenzar a detectar aplausos
        if self.running:
            return
        self.running = True
        self.stream  = sd.InputStream(
            channels=1,
            samplerate=44100,
            callback=self.callback,
            blocksize=1024,
            device=self.device  # None usa el dispositivo por defecto
        )
        self.stream.start()

    def stop(self):
        # Detiene el stream y libera el micrófono
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None