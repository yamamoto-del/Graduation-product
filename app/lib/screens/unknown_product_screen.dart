// lib/screens/unknown_product_screen.dart
// 不明JANコード時の手動入力画面

import 'package:flutter/material.dart';

class UnknownProductScreen extends StatefulWidget {
  final String janCode;
  final String productName; // 外部APIで取得した名前（空の場合あり）

  const UnknownProductScreen({
    super.key,
    required this.janCode,
    required this.productName,
  });

  @override
  State<UnknownProductScreen> createState() => _UnknownProductScreenState();
}

class _UnknownProductScreenState extends State<UnknownProductScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameCtrl;
  final _priceCtrl = TextEditingController();
  final _supplierCtrl = TextEditingController();
  final _unitCtrl = TextEditingController(text: '個');
  final _qtyCtrl = TextEditingController(text: '1');

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.productName);
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _priceCtrl.dispose();
    _supplierCtrl.dispose();
    _unitCtrl.dispose();
    _qtyCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.pop(context, {
      'product_name': _nameCtrl.text.trim(),
      'unit_price': double.tryParse(_priceCtrl.text) ?? 0.0,
      'supplier': _supplierCtrl.text.trim(),
      'unit': _unitCtrl.text.trim(),
      'quantity': int.tryParse(_qtyCtrl.text) ?? 1,
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF16213E),
        title: const Text('不明商品 — 手入力', style: TextStyle(color: Colors.white)),
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.withOpacity(0.4)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.warning_amber, color: Colors.orange, size: 16),
                        SizedBox(width: 6),
                        Text('マスタ未登録の商品',
                            style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text('JAN: ${widget.janCode}',
                        style: const TextStyle(color: Colors.grey, fontSize: 12)),
                    if (widget.productName.isNotEmpty)
                      Text('外部APIで取得: ${widget.productName}',
                          style: const TextStyle(color: Colors.grey, fontSize: 12)),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              _field(
                controller: _nameCtrl,
                label: '商品名 *',
                validator: (v) => (v == null || v.trim().isEmpty) ? '商品名を入力してください' : null,
              ),
              const SizedBox(height: 16),

              _field(
                controller: _priceCtrl,
                label: '仕入単価（円）',
                keyboardType: TextInputType.number,
                hint: '0',
              ),
              const SizedBox(height: 16),

              _field(
                controller: _supplierCtrl,
                label: '仕入先',
                hint: '（省略可）',
              ),
              const SizedBox(height: 16),

              _field(
                controller: _unitCtrl,
                label: '単位',
                hint: '個',
              ),
              const SizedBox(height: 16),

              _field(
                controller: _qtyCtrl,
                label: '数量',
                keyboardType: TextInputType.number,
                validator: (v) {
                  final n = int.tryParse(v ?? '');
                  if (n == null || n < 1) return '1以上の数量を入力してください';
                  return null;
                },
              ),
              const SizedBox(height: 32),

              ElevatedButton.icon(
                onPressed: _submit,
                icon: const Icon(Icons.add_shopping_cart),
                label: const Text('この商品を追加する', style: TextStyle(fontSize: 16)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF4F9EFF),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '※ 確定後、弥生販売の商品マスタにも自動登録されます。',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey, fontSize: 11),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _field({
    required TextEditingController controller,
    required String label,
    String? hint,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) =>
      TextFormField(
        controller: controller,
        keyboardType: keyboardType,
        style: const TextStyle(color: Colors.white),
        decoration: InputDecoration(
          labelText: label,
          hintText: hint,
          labelStyle: const TextStyle(color: Colors.grey),
          hintStyle: const TextStyle(color: Colors.grey),
          filled: true,
          fillColor: const Color(0xFF16213E),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: BorderSide(color: Colors.grey.withOpacity(0.3)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: Color(0xFF4F9EFF)),
          ),
        ),
        validator: validator,
      );
}
