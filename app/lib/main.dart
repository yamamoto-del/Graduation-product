// lib/main.dart
// アプリエントリポイント

import 'package:flutter/material.dart';
import 'services/api_service.dart';
import 'screens/setup_screen.dart';
import 'screens/scan_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiService().loadSettings();
  runApp(const JanScannerApp());
}

class JanScannerApp extends StatelessWidget {
  const JanScannerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JANスキャナー',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        colorScheme: ColorScheme.dark(
          primary: const Color(0xFF4F9EFF),
          surface: const Color(0xFF16213E),
        ),
        scaffoldBackgroundColor: const Color(0xFF1A1A2E),
      ),
      // 設定済みなら直接スキャン画面へ、未設定なら初回設定画面へ
      home: ApiService().isConfigured
          ? const ScanScreen()
          : const SetupScreen(),
    );
  }
}
