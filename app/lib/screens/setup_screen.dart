// lib/screens/setup_screen.dart
// 初回設定画面: サーバーIP + PINコード入力

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'scan_screen.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _urlCtrl = TextEditingController(text: 'http://192.168.1.100:8765');
  final _pinCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _urlCtrl.dispose();
    _pinCtrl.dispose();
    super.dispose();
  }

  Future<void> _connect() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });

    final api = ApiService();
    await api.saveSettings(_urlCtrl.text.trim(), _pinCtrl.text.trim());

    try {
      final health = await api.healthCheck();
      final yayoi = health['yayoi_running'] == true;

      if (!mounted) return;

      if (!yayoi) {
        setState(() {
          _error = '警告: 弥生販売が起動していません。\nRPA機能が使えない場合があります。';
          _loading = false;
        });
        // 警告はあるが続行可能
        await Future.delayed(const Duration(seconds: 2));
      }

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const ScanScreen()),
      );
    } catch (e) {
      setState(() {
        _error = 'サーバーに接続できません。\nIPアドレスとPINを確認してください。\n\n$e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(32),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.qr_code_scanner, size: 64, color: Color(0xFF4F9EFF)),
                  const SizedBox(height: 16),
                  const Text(
                    'JANスキャナー\n仕入管理システム',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 22, fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '初回設定',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 14, color: Colors.grey),
                  ),
                  const SizedBox(height: 40),

                  // サーバーURL
                  TextFormField(
                    controller: _urlCtrl,
                    style: const TextStyle(color: Colors.white),
                    decoration: _inputDeco(
                      label: 'サーバーURL',
                      hint: 'http://192.168.1.100:8765',
                      icon: Icons.computer,
                    ),
                    validator: (v) =>
                        (v == null || v.isEmpty) ? 'URLを入力してください' : null,
                    keyboardType: TextInputType.url,
                  ),
                  const SizedBox(height: 16),

                  // PIN
                  TextFormField(
                    controller: _pinCtrl,
                    style: const TextStyle(color: Colors.white),
                    decoration: _inputDeco(
                      label: 'PINコード（4〜6桁）',
                      hint: '例: 1234',
                      icon: Icons.lock_outline,
                    ),
                    obscureText: true,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    validator: (v) {
                      if (v == null || v.length < 4) return '4桁以上のPINを入力してください';
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),

                  if (_error != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.orange.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.orange.withOpacity(0.5)),
                      ),
                      child: Text(
                        _error!,
                        style: const TextStyle(color: Colors.orange, fontSize: 13),
                      ),
                    ),

                  const SizedBox(height: 16),

                  ElevatedButton(
                    onPressed: _loading ? null : _connect,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF4F9EFF),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: _loading
                        ? const SizedBox(
                            height: 20, width: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('接続する', style: TextStyle(fontSize: 16)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDeco({
    required String label,
    required String hint,
    required IconData icon,
  }) =>
      InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: Icon(icon, color: Colors.grey),
        labelStyle: const TextStyle(color: Colors.grey),
        hintStyle: const TextStyle(color: Colors.grey),
        filled: true,
        fillColor: const Color(0xFF16213E),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFF4F9EFF)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: Colors.grey.withOpacity(0.3)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFF4F9EFF)),
        ),
        counterStyle: const TextStyle(color: Colors.grey),
      );
}
