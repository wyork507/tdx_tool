環境建置說明
=================

目標：使用 `conda` 在 Windows 上建立與 macOS 相同的開發環境（由專案根目錄的 `environment.yml` 定義）。

先決條件
- 已安裝 Miniconda 或 Anaconda，且 `conda` 可於 PowerShell 中使用。

快速步驟（PowerShell）

```powershell
# 於專案根目錄執行腳本（會讀取 environment.yml）
.\scripts\create_conda_env.ps1

# 建立成功後，啟用環境
conda activate tdx-dev

# 若要手動安裝，可改用：
pip install -r requirements-dev.txt
```

說明
- `environment.yml` 已包含主要依賴；建立腳本會再安裝 `requirements-dev.txt`，把專案本體與開發套件一起裝進環境。
- 若環境已存在，腳本會提示是否先移除再重建。
- 若您在 macOS 上有額外手動安裝或本機專屬設定（例如 mac-only brew 包、系統字型、或某些 C 庫），請手動在 Windows 上以對應方式安裝。

驗證
- 啟用環境後，可執行：

```powershell
python -c "import sys, pandas as pd; print(sys.version); print(pd.__version__)"
```

進階
- 若需要使用 `pyproject.toml` 內的開發依賴或本套件可編輯安裝，請使用：

```powershell
pip install -e .[dev]
```
