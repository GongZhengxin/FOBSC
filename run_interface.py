import subprocess
import os

def activate_and_run():
    home = os.path.dirname(os.path.abspath(__file__))
    interface_path = os.path.join(home, "interface.py")
    # 激活虚拟环境并运行 Python 脚本
    command = f'conda activate fob_kilosort && python {interface_path}'
    # 执行命令
    subprocess.run(command, shell=True)

if __name__ == "__main__":
    activate_and_run()