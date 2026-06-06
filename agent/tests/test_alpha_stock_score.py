from src.api.alpha_stock_score import bare_code, score_label, to_ts_code


def test_to_ts_code_sh_main():
    assert to_ts_code("688017") == "688017.SH"
    assert to_ts_code("601689") == "601689.SH"


def test_to_ts_code_sz_gem():
    assert to_ts_code("300124") == "300124.SZ"
    assert to_ts_code("002472") == "002472.SZ"


def test_to_ts_code_passthrough():
    assert to_ts_code("688017.SH") == "688017.SH"


def test_bare_code():
    assert bare_code("688017.SH") == "688017"
    assert bare_code("002472") == "002472"


def test_score_label_buckets():
    assert score_label(85) == "偏强"
    assert score_label(55) == "中性"
    assert score_label(20) == "偏弱"
