// lib/services/api_service.dart
// FastAPI サーバーとの通信クライアント

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const _keyServerUrl = 'server_url';
  static const _keyPin = 'pin';

  String _serverUrl = '';
  String _pin = '';

  // シングルトン
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  // ── 初期化 ─────────────────────────────────────────────

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _serverUrl = prefs.getString(_keyServerUrl) ?? '';
    _pin = prefs.getString(_keyPin) ?? '';
  }

  Future<void> saveSettings(String serverUrl, String pin) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyServerUrl, serverUrl);
    await prefs.setString(_keyPin, pin);
    _serverUrl = serverUrl;
    _pin = pin;
  }

  bool get isConfigured => _serverUrl.isNotEmpty && _pin.isNotEmpty;
  String get serverUrl => _serverUrl;

  // ── 共通ヘッダー ────────────────────────────────────────

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'X-PIN': _pin,
  };

  Uri _uri(String path) => Uri.parse('$_serverUrl$path');

  // ── ヘルスチェック ──────────────────────────────────────

  Future<Map<String, dynamic>> healthCheck() async {
    final resp = await http.get(_uri('/health')).timeout(const Duration(seconds=5));
    return json.decode(resp.body) as Map<String, dynamic>;
  }

  // ── 商品検索 ────────────────────────────────────────────

  Future<Map<String, dynamic>> getProduct(String janCode) async {
    final resp = await http
        .get(_uri('/products/$janCode'), headers: _headers)
        .timeout(const Duration(seconds: 8));
    if (resp.statusCode != 200) _throwError(resp);
    return json.decode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
  }

  // ── セッション ──────────────────────────────────────────

  Future<Map<String, dynamic>> createSession(String createdBy) async {
    final resp = await http
        .post(
          _uri('/sessions'),
          headers: _headers,
          body: json.encode({'created_by': createdBy}),
        )
        .timeout(const Duration(seconds: 5));
    if (resp.statusCode != 201) _throwError(resp);
    return json.decode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getSession(String sessionId) async {
    final resp = await http
        .get(_uri('/sessions/$sessionId'), headers: _headers)
        .timeout(const Duration(seconds: 5));
    if (resp.statusCode != 200) _throwError(resp);
    return json.decode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getSessionItems(String sessionId) async {
    final resp = await http
        .get(_uri('/sessions/$sessionId/items'), headers: _headers)
        .timeout(const Duration(seconds: 5));
    if (resp.statusCode != 200) _throwError(resp);
    return json.decode(utf8.decode(resp.bodyBytes)) as List<dynamic>;
  }

  Future<Map<String, dynamic>> addSessionItem({
    required String sessionId,
    required String janCode,
    required int quantity,
    String? productName,
    double? unitPrice,
    String? supplier,
    String? unit,
  }) async {
    final body = <String, dynamic>{
      'jan_code': janCode,
      'quantity': quantity,
      if (productName != null) 'product_name': productName,
      if (unitPrice != null) 'unit_price': unitPrice,
      if (supplier != null) 'supplier': supplier,
      if (unit != null) 'unit': unit,
    };
    final resp = await http
        .post(
          _uri('/sessions/$sessionId/items'),
          headers: _headers,
          body: json.encode(body),
        )
        .timeout(const Duration(seconds: 8));
    if (resp.statusCode != 201) _throwError(resp);
    return json.decode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
  }

  Future<void> deleteSessionItem(String sessionId, int itemId) async {
    final resp = await http
        .delete(_uri('/sessions/$sessionId/items/$itemId'), headers: _headers)
        .timeout(const Duration(seconds: 5));
    if (resp.statusCode != 200) _throwError(resp);
  }

  Future<Map<String, dynamic>> confirmSession(String sessionId) async {
    final resp = await http
        .post(_uri('/sessions/$sessionId/confirm'), headers: _headers)
        .timeout(const Duration(seconds: 10));
    if (resp.statusCode != 200) _throwError(resp);
    return json.decode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
  }

  // ── RPAキュー ───────────────────────────────────────────

  Future<Map<String, dynamic>> getQueueStatus() async {
    final resp = await http
        .get(_uri('/rpa/queue'), headers: _headers)
        .timeout(const Duration(seconds: 5));
    if (resp.statusCode != 200) _throwError(resp);
    return json.decode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
  }

  // ── エラー ──────────────────────────────────────────────

  void _throwError(http.Response resp) {
    final body = json.decode(utf8.decode(resp.bodyBytes));
    final detail = body['detail'] ?? 'エラーが発生しました';
    throw ApiException(resp.statusCode, detail.toString());
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException($statusCode): $message';
}
