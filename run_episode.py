import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent

def run_script(script_name):
    print("\n" + "=" * 60)
    print(f"▶️ Lancement de {script_name}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, script_name],
        cwd=PROJECT_DIR
    )

    if result.returncode != 0:
        print(f"\n❌ Erreur dans {script_name}")
        sys.exit(result.returncode)

    print(f"✅ {script_name} terminé")

def main():
    print("\n🎬 YOUTUBE AUTOMATION — GÉNÉRATEUR D'ÉPISODE")
    print("=" * 60)

    run_script("episode_generator.py")
    run_script("generate_episode_audio.py")
    run_script("make_animatic.py")

    print("\n" + "=" * 60)
    print("🎉 ÉPISODE COMPLET TERMINÉ !")
    print("=" * 60)
    print("📹 videos/episode_animatic.mp4")

if __name__ == "__main__":
    main()
