# contract_checker/prompt.py
CONTRACT_PROMPT = (
    "你是合同审核专家，请从图像中精确提取以下信息。请严格遵守以下规则：\n"
    "1. 若某项内容存在但字迹潦草、无法辨认，请填写「（签名模糊）」；\n"
    "2. 若某项内容完全缺失（无签字/无盖章/无文字），请留空字符串 ''；\n"
    "3. 日期格式统一为 YYYY-MM-DD；\n"
    "4. 关联主体如有多个，用中文逗号分隔。\n\n"

    "需提取的字段如下：\n"
    "- contract_name: 合同名称\n"
    "- contract_id: 合同编号\n"
    "- party_a_name: 甲方全称\n"
    "- party_b_name: 乙方全称\n"
    "- effective_start: 合同生效起始日\n"
    "- effective_end: 合同终止日\n"
    "- seal_party_a: 甲方盖章全称（含章类型，如‘中海油（北京）销售有限公司 合同专用章’）\n"
    "- seal_party_b: 乙方盖章全称\n"
    "- sign_party_a: 甲方签字人姓名（若字迹模糊无法辨认，填「（签名模糊）」）\n"
    "- sign_party_b: 乙方签字人姓名（若字迹模糊无法辨认，填「（签名模糊）」）\n"
    "- settlement_method: 结算方式（如‘款到发货’、‘预付款’等）\n"
    "- bank_account_name: 乙方收款账户名称\n"
    "- bank_name: 开户行全称\n"
    "- bank_account_number: 银行账号\n"
    "- payment_terms: 付款条件（如‘收到发票后30个工作日’）\n"
    "- goods_name: 货物/服务名称\n"
    "- quantity: 数量及单位（如‘22.95吨’）\n"
    "- total_amount_incl_tax: 总含税金额（数字，如‘114291’）\n"
    "- related_entities: 合同关联主体列表（如‘中海油魏公村（北京）加油站有限公司’）\n\n"

    "请严格按以下 JSON 格式输出，不要包含任何额外说明：\n"
    "{\n"
    '  "contract_name": "",\n'
    '  "contract_id": "",\n'
    '  "party_a_name": "",\n'
    '  "party_b_name": "",\n'
    '  "effective_start": "",\n'
    '  "effective_end": "",\n'
    '  "seal_party_a": "",\n'
    '  "seal_party_b": "",\n'
    '  "sign_party_a": "",\n'
    '  "sign_party_b": "",\n'
    '  "settlement_method": "",\n'
    '  "bank_account_name": "",\n'
    '  "bank_name": "",\n'
    '  "bank_account_number": "",\n'
    '  "payment_terms": "",\n'
    '  "goods_name": "",\n'
    '  "quantity": "",\n'
    '  "total_amount_incl_tax": "",\n'
    '  "related_entities": ""\n'
    "}"
)