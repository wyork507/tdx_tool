# 測試指南

本文檔說明如何為 tdx_tool 專案編寫和執行測試。

## 📁 測試結構

```
tests/
├── __init__.py                 # 測試包初始化
├── conftest.py                 # Pytest 全局配置和 fixtures
├── test_authority.py           # 認證模組測試 (tdx_auth)
├── test_core.py                # 核心類測試 (tdx_tool)
├── test_bus.py                 # Bus 模組測試 (tdx_bus、BusRegion)
├── test_models.py              # 數據模型測試 (枚舉、Struct)
└── test_parsers.py             # 解析器測試 (數據轉換)
```

## 🚀 快速開始

### 1. 安裝開發依賴

```bash
# 使用 make
make install-dev

# 或直接使用 pip
pip install -e ".[dev]"
```

### 2. 運行所有測試

```bash
# 基本運行
make test

# 詳細輸出
make test-verbose

# 或直接使用 pytest
pytest
pytest -v
```

### 3. 運行特定測試

```bash
# 只測試認證模組
pytest tests/test_authority.py

# 運行特定的測試類
pytest tests/test_authority.py::TestTdxAuth

# 運行特定的測試方法
pytest tests/test_authority.py::TestTdxAuth::test_token_cached

# 使用模式匹配
pytest -k "token"  # 會運行所有包含 "token" 的測試
pytest -k "not network"  # 排除包含 "network" 的測試
```

### 4. 查看測試覆蓋率

```bash
# 安裝 coverage 工具
pip install pytest-cov

# 運行測試並生成覆蓋率報告
pytest --cov=src/tdx_tool --cov-report=html

# 見 htmlcov/index.html
```

## 🧪 測試類型詳解

### conftest.py - 共享 Fixtures

Pytest fixtures 是可重用的測試資源。已實現的 fixtures：

| Fixture | 用途 | 返回值 |
|---------|------|--------|
| `mock_logger` | Mock 日誌記錄器 | Mock Logger 物件 |
| `test_credentials` | 測試 API 認證信息 | `{"client_id": "...", "client_key": "..."}` |
| `mock_token` | Mock TDX API Token 回應 | Token 數據字典 |
| `mock_bus_response` | Mock 公車 API 回應 | 公車路線數據 |

使用方式：
```python
def test_example(mock_logger, test_credentials):  # 在參數中聲明
    # mock_logger 和 test_credentials 會被自動注入
    assert mock_logger is not None
```

### test_authority.py - 認證測試

測試 `tdx_auth` 類的令牌管理：

- ✅ `test_init_successful` - 成功初始化
- ✅ `test_token_cached` - Token 緩存機制
- ✅ `test_token_refresh_on_expiration` - Token 過期自動刷新
- ✅ `test_update_token_network_error` - 網絡錯誤處理
- ✅ `test_callable_interface` - 可調用介面
- ✅ `test_string_representation` - 字串表示

### test_core.py - 核心類測試

測試 `tdx_tool` 基類的核心功能：

**初始化和屬性：**
- ✅ `test_initialization` - 初始化檢查
- ✅ `test_export_result_setter_valid` - 布爾屬性設置
- ✅ `test_default_coor_setter_valid` - CRS 驗證
- ✅ `test_output_path_setter_valid` - 路徑設置

**API 請求和重試：**
- ✅ `test_get_data_from_suffix_url_success` - 成功請求
- ✅ `test_get_data_retry_on_401_unauthorized` - 401 Token 刷新重試
- ✅ `test_get_data_retry_on_429_rate_limit` - 429 速率限制重試（指數退避）
- ✅ `test_get_data_max_retries_exceeded` - 最大重試次數超限

### test_bus.py - 公車模組測試

測試 `tdx_bus` 類和 `BusRegion` 枚舉：

**tdx_bus 類：**
- ✅ `test_initialization_with_region` - 指定地區初始化
- ✅ `test_from_region_str_valid_region` - 從字串初始化
- ✅ `test_from_region_str_invalid_region` - 無效地區名稱處理
- ✅ `test_ambiguous_region_warning` - 模糊地區名稱警告

**BusRegion 枚舉：**
- ✅ `test_is_county_for_county_regions` - 縣份識別
- ✅ `test_ambiguous_name_for_hsinchu` - 模糊名稱檢測

### test_models.py - 數據模型測試

測試枚舉和 msgspec Struct 模型：

**枚舉：**
- ✅ `test_direction_enum_values` - 方向枚舉
- ✅ `test_bus_route_type_enum_values` - 路線類型枚舉
- ✅ `test_error_cause_enum_values` - 錯誤原因枚舉

**Struct 模型：**
- ✅ `test_i18n_creation_with_both_languages` - 雙語名稱
- ✅ `test_operator_creation` - 營運商模型
- ✅ `test_subroute_creation_full` - 子路線模型
- ✅ `test_route_with_multiple_operators` - 多營運商路線

### test_parsers.py - 解析器測試

測試數據轉換函數：

**路線解析：**
- ✅ `test_parse_routes_single_route_no_subroutes` - 解析單一路線
- ✅ `test_parse_routes_with_subroutes` - 解析包含子路線的路線
- ✅ `test_parse_routes_with_multiple_operators` - 多營運商路線解析

**幾何數據：**
- ✅ `test_parse_route_with_shape_valid_geometry` - 有效 WKT 幾何
- ✅ `test_parse_route_with_shape_invalid_geometry` - 無效幾何處理

**站點解析：**
- ✅ `test_parse_stations_basic` - 基本站點解析
- ✅ `test_parse_stations_multiple_stops` - 多站點解析

## 🎯 編寫新測試的指南

### 基本模式

```python
# 1. 導入必要的模組
import pytest
from unittest.mock import Mock, patch

# 2. 定義測試類（可選但推薦）
class TestMyFeature:
    """我的功能測試套件。"""
    
    # 3. 定義 fixtures（可選）
    @pytest.fixture
    def my_resource(self):
        """創建測試資源。"""
        return {"data": "test"}
    
    # 4. 編寫測試方法
    def test_something_works(self, my_resource):
        """測試某個功能。"""
        # Arrange - 準備
        expected = "test"
        
        # Act - 執行
        result = my_resource["data"]
        
        # Assert - 驗證
        assert result == expected
```

### 使用 Mock 和 Patch

```python
# Mock 外部依賴
from unittest.mock import Mock, patch

def test_api_call(self, mock_logger):
    """測試 API 調用。"""
    with patch('module.requests.get') as mock_get:
        # 設置 mock 行為
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        # 執行被測試程式碼
        # ...
        
        # 驗證 mock 被正確調用
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == "expected_url"
```

### 異常測試

```python
def test_invalid_input_raises_error(self):
    """測試無效輸入是否拋出異常。"""
    with pytest.raises(ValueError, match="Invalid value"):
        some_function("invalid")
```

### 參數化測試

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply(self, input, expected):
    """參數化測試。"""
    assert input * 2 == expected
```

## ✅ 測試覆蓋率目標

根據我們的評估，建議目標：

| 模組 | 覆蓋率目標 | 優先級 |
|------|----------|--------|
| `authority.py` | 90%+ | 🔴 高 |
| `core.py` | 85%+ | 🔴 高 |
| `bus.py` | 80%+ | 🟠 中 |
| `parsers.py` | 85%+ | 🟠 中 |
| `models.py` | 95%+ | 🟡 低 |

## 🔍 常見 Mock 技巧

### Mock HTTP 請求

```python
with patch('requests.get') as mock_get:
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    # 現在調用使用 requests.get 的程式碼
```

### Mock init 方法

```python
with patch('module.ClassName.__init__', return_value=None):
    obj = ClassName()  # __init__ 被跳過
    # 手動設置屬性
    obj.attribute = "value"
```

### Mock 屬性

```python
mock_obj = Mock()
type(mock_obj).property_name = PropertyMock(return_value="value")
```

## 📊 CI/CD 集成

### GitHub Actions 工作流程示例

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run tests
        run: |
          pytest --cov=src/tdx_tool --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 🐛 故障排除

### ImportError: No module named 'src.tdx_tool'

確保在正確的目錄運行測試：
```bash
cd /path/to/tdx_tool  # 專案根目錄
pytest
```

### ModuleNotFoundError in tests

安裝包為可編輯模式：
```bash
pip install -e .
```

### Mock 不起作用

確保 patch 路徑正確（patch 使用的位置，不是定義的位置）：
```python
# ❌ 錯誤
patch('requests.get')

# ✅ 正確
patch('src.tdx_tool.core.requests.get')  # 在 core.py 中導入 requests
```

## 📚 參考資源

- [Pytest 官方文檔](https://docs.pytest.org/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [测试驱动开发 (TDD)](https://en.wikipedia.org/wiki/Test-driven_development)
