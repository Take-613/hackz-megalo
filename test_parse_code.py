import os
import warnings
from pathlib import Path
import pretty_midi
import numpy as np
from scipy.io import wavfile
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

# 🚨 超重要：basic-pitchに「ONNXエンジンを使え！」と強制する
os.environ["BASIC_PITCH_MODEL_TYPE"] = "onnx"

# 余計な警告文を非表示にする
warnings.filterwarnings("ignore")

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")

def midi_to_wav(midi_path, wav_path):
    """MIDIデータをWAV音声（サイン波）に変換して保存する"""
    midi_data = pretty_midi.PrettyMIDI(str(midi_path))
    audio_data = midi_data.synthesize(fs=44100)
    
    # WAVファイルとして正しく書き出せるように、音量を正規化して16bit形式にする
    audio_data_int16 = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
    wavfile.write(str(wav_path), 44100, audio_data_int16)

def main():
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    mid_files = list(INPUT_DIR.glob("*.mid"))

    if not mid_files:
        print("⚠️ inputフォルダに .mid ファイルが見つかりません。")
        return

    print(f"🎹 {len(mid_files)}件のMIDIファイルをWAVに変換してAI解析します...\n")

    for midi_path in mid_files:
        print(f"処理中 ⏳: {midi_path.name}")
        
        temp_wav_path = INPUT_DIR / f"{midi_path.stem}_temp.wav"
        
        # 1. MIDI -> WAV 変換
        try:
            print("  -> 🔊 WAVファイル(音声)に変換中...")
            midi_to_wav(midi_path, temp_wav_path)
        except Exception as e:
            print(f"❌ MIDI変換エラー: {e}")
            continue

        # 2. WAV -> basic-pitch で解析
        try:
            print("  -> 🧠 basic-pitch(ONNX)でAI解析中...")
            predict_and_save(
                audio_path_list=[str(temp_wav_path)],
                output_directory=str(OUTPUT_DIR),
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False,
                model_or_model_path=ICASSP_2022_MODEL_PATH  # 🚨 ここを修正しました！(.onnxを外した)
            )
            
            # basic-pitch は _basic_pitch.mid という名前で出力します
            expected_output = OUTPUT_DIR / f"{temp_wav_path.stem}_basic_pitch.mid"
            print(f"✅ 完了 ✨: {expected_output.name} を出力しました！\n")
            
        except Exception as e:
            print(f"❌ AI解析エラー: {e}\n")
            
        finally:
            # お掃除
            if temp_wav_path.exists():
                try:
                    temp_wav_path.unlink()
                except Exception as e:
                    pass

if __name__ == "__main__":
    main()