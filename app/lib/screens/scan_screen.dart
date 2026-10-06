// lib/screens/scan_screen.dart
// JANコードスキャン画面 + セッション管理

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../services/api_service.dart';
import 'unknown_product_screen.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final _api = ApiService();
  final _scannerCtrl = MobileScannerController();

  String? _sessionId;
  List<Map<String, dynamic>> _items = [];
  bool _scanning = true;
  bool _processing = false;
  String _lastJan = '';
  int _queueLength = 0;

  // セッションタイムアウト: 30分
  Timer? _timeoutTimer;
  static const _timeoutDuration = Duration(minutes: 30);

  @override
  void initState() {
    super.initState();
    _startSession();
  }

  @override
  void dispose() {
    _scannerCtrl.dispose();
    _timeoutTimer?.cancel();
    super.dispose();
  }

  void _resetTimeout() {
    _timeoutTimer?.cancel();
    _timeoutTimer = Timer(_timeoutDuration, _onTimeout);
  }

  void _onTimeout() {
    if (!mounted) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        title: const Text('セッションタイムアウト'),
        content: const Text(
          '30分間操作がなかったためセッションを終了しました。\n'
          'スキャンデータはサーバーに下書き保存されています。',
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _startSession();
            },
            child: const Text('新しいセッションを開始'),
          ),
        ],
      ),
    );
  }

  // ── セッション作成 ──────────────────────────────────────

  Future<void> _startSession() async {
    try {
      final result = await _api.createSession('スタッフ');
      setState(() {
        _sessionId = result['id'];
        _items = [];
      });
      _resetTimeout();
    } catch (e) {
      _showError('セッションを作成できませんでした: $e');
    }
  }

  // ── スキャン処理 ────────────────────────────────────────

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_processing || !_scanning) return;
    final code = capture.barcodes.firstOrNull?.rawValue;
    if (code == null || code == _lastJan) return;
    _lastJan = code;

    setState(() { _processing = true; });
    _resetTimeout();

    try {
      // 商品情報を取得
      final product = await _api.getProduct(code);

      if (!mounted) return;

      if (product['is_unknown'] == true) {
        // 不明商品 → 手動入力画面へ
        setState(() { _scanning = false; });
        final result = await Navigator.push<Map<String, dynamic>?>(
          context,
          MaterialPageRoute(
            builder: (_) => UnknownProductScreen(
              janCode: code,
              productName: product['product_name'] ?? '',
            ),
          ),
        );
        setState(() { _scanning = true; });

        if (result == null) {
          setState(() { _processing = false; });
          return;
        }

        await _addItemDialog(code, product: product, overrides: result);
      } else {
        await _showQuantityDialog(code, product);
      }
    } catch (e) {
      _showError('エラー: $e');
    } finally {
      await Future.delayed(const Duration(seconds: 2));
      setState(() { _processing = false; _lastJan = ''; });
    }
  }

  Future<void> _showQuantityDialog(String jan, Map<String, dynamic> product) async {
    final qtyCtrl = TextEditingController(text: '1');
    final qty = await showDialog<int>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('数量を入力'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              product['product_name'] ?? '',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
            ),
            Text('単価: ¥${(product['unit_price'] ?? 0).toStringAsFixed(0)}',
                style: const TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 16),
            TextField(
              controller: qtyCtrl,
              keyboardType: TextInputType.number,
              autofocus: true,
              decoration: const InputDecoration(
                labelText: '数量',
                suffixText: '個',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('キャンセル')),
          ElevatedButton(
            onPressed: () {
              final v = int.tryParse(qtyCtrl.text);
              if (v != null && v > 0) Navigator.pop(context, v);
            },
            child: const Text('追加'),
          ),
        ],
      ),
    );
    if (qty == null) return;
    await _addItemDialog(jan, product: product, qty: qty);
  }

  Future<void> _addItemDialog(
    String jan, {
    required Map<String, dynamic> product,
    Map<String, dynamic>? overrides,
    int qty = 1,
  }) async {
    if (_sessionId == null) return;
    try {
      final result = await _api.addSessionItem(
        sessionId: _sessionId!,
        janCode: jan,
        quantity: overrides != null ? (overrides['quantity'] ?? qty) : qty,
        productName: overrides?['product_name'],
        unitPrice: overrides?['unit_price'] != null
            ? (overrides!['unit_price'] as num).toDouble()
            : null,
        supplier: overrides?['supplier'],
        unit: overrides?['unit'],
      );
      setState(() {
        _items.add(result);
      });
    } catch (e) {
      _showError('追加に失敗しました: $e');
    }
  }

  // ── 伝票確定 ────────────────────────────────────────────

  Future<void> _confirmSlip() async {
    if (_sessionId == null || _items.isEmpty) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('伝票確定'),
        content: Text('${_items.length} 件の商品を弥生販売に登録します。よろしいですか？'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('キャンセル')),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.blue),
            child: const Text('確定'),
          ),
        ],
      ),
    );
    if (ok != true) return;

    try {
      final result = await _api.confirmSession(_sessionId!);
      final pos = result['queue_position'] ?? 1;
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('伝票を確定しました。RPAが処理します（待機: $pos 件）'),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 4),
      ));
      _startSession(); // 新しいセッションを開始
    } catch (e) {
      _showError('確定に失敗しました: $e');
    }
  }

  // ── 削除 ────────────────────────────────────────────────

  Future<void> _deleteItem(int index) async {
    if (_sessionId == null) return;
    final item = _items[index];
    try {
      await _api.deleteSessionItem(_sessionId!, item['id'] as int);
      setState(() { _items.removeAt(index); });
      _resetTimeout();
    } catch (e) {
      _showError('削除に失敗しました: $e');
    }
  }

  void _showError(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: Colors.red,
    ));
  }

  // ── UI ──────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF16213E),
        title: const Text('JANスキャン', style: TextStyle(color: Colors.white)),
        actions: [
          if (_queueLength > 0)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(
                child: Text(
                  'RPA待機: $_queueLength件',
                  style: const TextStyle(color: Colors.orange, fontSize: 12),
                ),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.check_circle_outline, color: Colors.greenAccent),
            tooltip: '伝票確定',
            onPressed: _items.isNotEmpty ? _confirmSlip : null,
          ),
        ],
      ),
      body: Column(
        children: [
          // カメラプレビュー
          SizedBox(
            height: 220,
            child: Stack(
              children: [
                MobileScanner(
                  controller: _scannerCtrl,
                  onDetect: _onDetect,
                ),
                if (_processing)
                  Container(
                    color: Colors.black54,
                    child: const Center(
                      child: CircularProgressIndicator(color: Colors.white),
                    ),
                  ),
                Positioned(
                  bottom: 8, left: 0, right: 0,
                  child: Center(
                    child: Text(
                      'JANコードをカメラに向けてください',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.8),
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // スキャンアイテム一覧
          Expanded(
            child: _items.isEmpty
                ? const Center(
                    child: Text(
                      'スキャンした商品がここに表示されます',
                      style: TextStyle(color: Colors.grey),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: _items.length,
                    itemBuilder: (_, i) {
                      final item = _items[i];
                      return Card(
                        color: const Color(0xFF16213E),
                        margin: const EdgeInsets.symmetric(vertical: 4),
                        child: ListTile(
                          title: Text(
                            item['product_name'] ?? '',
                            style: const TextStyle(color: Colors.white, fontSize: 14),
                          ),
                          subtitle: Text(
                            '${item['jan_code']}  ×${item['quantity']}  '
                            '¥${(item['unit_price'] ?? 0).toStringAsFixed(0)}',
                            style: const TextStyle(color: Colors.grey, fontSize: 12),
                          ),
                          trailing: IconButton(
                            icon: const Icon(Icons.delete_outline, color: Colors.redAccent, size: 20),
                            onPressed: () => _deleteItem(i),
                          ),
                          leading: item['is_unknown'] == true
                              ? const Icon(Icons.warning_amber, color: Colors.orange, size: 20)
                              : const Icon(Icons.check_circle, color: Colors.greenAccent, size: 20),
                        ),
                      );
                    },
                  ),
          ),

          // 確定ボタン
          if (_items.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _confirmSlip,
                  icon: const Icon(Icons.send),
                  label: Text('${_items.length} 件の伝票を確定する'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF4F9EFF),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
