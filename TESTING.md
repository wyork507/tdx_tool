## 🚀 測試快速入門

### 📊 當前測試覆蓋

已建立的測試統計：

| 模組 | 測試數 | 狀態 |
|------|--------|------|
| `test_authority.py` | 6 | ✅ |
| `test_core.py` | 13 | ✅ |
| `test_bus.py` | 16 | ✅ |
| `test_models.py` | 14 | ✅ |
| `test_parsers.py` | 8 | ✅ |
| **總計** | **57** | **✅ 全部就緒** |

### 💡 一分鐘快速開始

```bash
# 1. 安裝依賴（如果還沒安裝的話）
pip install -e ".[dev]"

# 2. 運行全部測試
pytest

# 3. 查看詳細結果
pytest -v

# 4. 運行特定模組測試
pytest tests/test_authority.py -v
pytest tests/test_models.py -v

# 5. 運行特定測試
pytest tests/test_authority.py::TestTdxAuth::test_token_cached -v

# 6. 測試覆蓋率
pip install pytest-cov
pytest --cov=src/tdx_tool
```

### 📝 測試重點說明

#### 1️⃣ **認證測試** (`test_authority.py`)
重點測試 Token 管理機制：
- Token 快取行為
- 自動刷新機制
- 網絡錯誤處理

```python
# 常見情景測試
✅ Token 初始化并快取
✅ Token 過期自動刷新
✅ API 錯誤重試（401、429）
```

#### 2️⃣ **核心類測試** (`test_core.py`)
重點測試 API 請求和屬性驗證：
- 屬性 setter 驗證（布爾值、CRS、路徑）
- HTTP 請求和重試機制
- 指數退避算法（429 速率限制）

```python
# 常見情景測試
✅ 速率限制重試（指數退避）
✅ Token 過期刷新和重試
✅ 屬性驗證和錯誤處理
```

#### 3️⃣ **公車模組測試** (`test_bus.py`)
重點測試區域管理和初始化：
- 地區初始化
- 模糊地區名稱處理
- 從字串初始化

```python
# 常見情景測試
✅ 支援多種地區名稱格式
✅ 檢測並警告模糊地區
✅ BusRegion 枚舉正確性
```

#### 4️⃣ **數據模型測試** (`test_models.py`)
重點測試枚舉和 msgspec Struct：
- 枚舉值驗證
- 多語言支持
- 複雜數據結構

```python
# 常見情景測試
✅ 所有枚舉值正確
✅ I18n 雙語支持
✅ 複雜嵌套結構
```

#### 5️⃣ **解析器測試** (`test_parsers.py`)
重點測試數據轉換：
- 路線解析
- WKT 幾何處理
- 站點數據提取

```python
# 常見情景測試
✅ 單一/多子路線解析
✅ 有效/無效幾何處理
✅ 站點數據展平
```

### 🎯 推薦的測試習慣

#### 開發前 (TDD)
```bash
# 先寫測試，再實現功能
pytest -k "your_new_test" -v  # 應該失敗
# ... 實现功能 ...
pytest -k "your_new_test" -v  # 應該通過
```

#### 提交代碼前
```bash
# 確保所有測試通過
pytest -v

# 檢查代碼品質
make lint
make type-check
```

#### Code Review
```bash
# 檢查測試覆蓋率
pytest --cov=src/tdx_tool --cov-report=term-missing
```

### 🔧 常見問題解決

**Q: `ModuleNotFoundError: No module named 'src'`**
```bash
# 確保安裝為可編輯模式
pip install -e .
```

**Q: Mock 不工作**
```python
# ✅ 正確：patch 在使用的位置
with patch('src.tdx_tool.core.requests.get'):
    ...

# ❌ 錯誤：patch 在定義的位置
with patch('requests.get'):
    ...
```

**Q: 測試太慢**
```bash
# 只運行快速測試
pytest -m "not slow"

# 並行執行測試
pip install pytest-xdist
pytest -n auto
```

### 🗺️ 下一步建議

1. **✅ 已完成：基礎單元測試** (57 個測試)
2. 🔄 **待實施：集成測試** - 真實 API 調用測試
3. 🔄 **待實施：性能測試** - 大數據集處理
4. 🔄 **待實施：GitHub Actions** - 自動化 CI/CD
5. 🔄 **待實施：E2E 測試** - 端到端測試場景

### 📚 延伸學習

- **Mock 技巧**: 查看 `conftest.py` 中的 fixtures 定義
- **測試模式**: 查看各個 `test_*.py` 文件中的註解和範例
- **進階 Pytest**: 查看 `tests/README.md` 中的完整指南
