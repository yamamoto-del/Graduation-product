import {
  H1, H2, Text, Card, CardHeader, CardBody,
  Row, Grid, Stack, Table, Pill, Callout, Divider, Stat, Spacer,
  useHostTheme,
} from "cursor/canvas";
import type { CSSProperties } from "cursor/canvas";
import type { ReactNode } from "react";

// ─── Data ───────────────────────────────────────────────────────────────────

const TECH_STACK_HEADERS: ReactNode[] = ["コンポーネント", "技術", "実行環境"];
const TECH_STACK_ROWS: ReactNode[][] = [
  ["モバイルアプリ",    "Flutter (Dart)",              "Android / iOS"],
  ["PCサーバー",        "Python 3.11 + FastAPI",       "Windows 10/11"],
  ["商品マスタDB",      "SQLite",                      "PCサーバー上"],
  ["RPA自動化",         "pywinauto",                   "Windows 10/11"],
  ["JAN検索（一次）",   "楽天ウェブサービスAPI",        "インターネット"],
  ["JAN検索（補助）",   "Open Food Facts API",         "インターネット"],
  ["在庫・販売管理",    "弥生販売（既存）",             "Windowsデスクトップ"],
];

const DECISIONS_HEADERS: ReactNode[] = ["項目", "決定内容", "理由"];
const DECISIONS_ROWS: ReactNode[][] = [
  ["在庫の正者",           "弥生販売のみ",                "二重管理を防ぎ既存業務フローを維持"],
  ["アプリ形態",           "Flutter ネイティブ",          "Android/iOS共通コード・カメラAPI安定性"],
  ["RPA方式",              "Python pywinauto",            "追加コストゼロ・Pythonエコシステム統合"],
  ["弥生販売バージョン",   "弥生販売 26 に固定",          "pywinautoのUI操作はバージョン依存のため"],
  ["マスタ同期",           "RPA実行後に即時再同期",       "常に最新状態・定期バッチ不要"],
  ["数量入力",             "1スキャン後に手動入力",       "段ボール単位など現場の数え方に対応"],
  ["ネットワーク",         "固定IP + 初回手動設定",       "シンプルで安定・追加インフラ不要"],
  ["マルチユーザー",       "セッション方式",              "複数人での同一伝票作業に対応"],
  ["セッションタイムアウト","30分で自動タイムアウト",     "未確定データは下書き保存して作業継続可能"],
  ["RPA排他制御",          "asyncio.Queue キュー方式",    "弥生販売への同時操作を防ぐ"],
  ["RPA失敗時",            "ログ保存+PC画面アラート+手動再実行",  "状態不定を防ぎ弥生販売の二重登録を回避"],
  ["サーバー認証",         "PINコード（4〜6桁）",         "同一Wi-Fi内の不正アクセスを防ぐ"],
  ["不明JAN対応",          "楽天API→OFF→手動→RPA登録",   "入荷を止めずにマスタを自動拡充"],
];

const NFR_HEADERS: ReactNode[] = ["分類", "仕様", "詳細"];
const NFR_ROWS: ReactNode[][] = [
  ["RPA排他制御",   "asyncio.Queue キュー方式",       "伝票確定を受けたらキューに積み、1件ずつ順番にRPA実行。スマホには待機件数を表示"],
  ["RPA失敗リカバリ", "ログ記録 + アラート + 手動再実行", "処理ステップをSQLiteにログ記録。失敗時はPC画面にアラート表示し、管理画面から手動再実行が可能。送信済みフラグで二重登録を防止"],
  ["サーバー認証",  "PINコード（4〜6桁）",            "初回設定時にPINを設定。Flutter初回起動時にPIN入力→以降は全APIリクエストのHeaderにPINを付与"],
  ["セッション管理","タイムアウト30分 + 下書き保存",  "最終操作から30分でセッション自動終了。未確定スキャンデータはサーバーに下書きとして保存し、次回起動時に復元可能"],
  ["バージョン固定","弥生販売 26 対象",               "起動時に弥生販売のウィンドウタイトルでバージョンを自動確認。対象外バージョンは警告を表示して停止"],
  ["ヘルスチェック","GET /health エンドポイント",     "Flutter起動時にサーバーの疎通・バージョンを確認。弥生販売の起動確認も含む"],
];

const FLOW_NORMAL = [
  { step: "1", actor: "スタッフ",  action: "Flutter アプリ（PIN認証済み）/ USB リーダーで JANコードをスキャン" },
  { step: "2", actor: "アプリ",    action: "PCサーバー（固定IP）へ JANコード + PINヘッダーを送信（Wi-Fi）" },
  { step: "3", actor: "サーバー",  action: "PIN検証 → SQLite の商品マスタDBを照合し商品情報を返す" },
  { step: "4", actor: "スタッフ",  action: "アプリ画面で数量を手入力し「追加」（30分無操作でタイムアウト・下書き保存）" },
  { step: "5", actor: "スタッフ",  action: "全商品スキャン完了後「伝票確定」ボタンを押す" },
  { step: "6", actor: "サーバー",  action: "仕入伝票データを組み立て asyncio.Queue に積む（待機件数をスマホに返す）" },
  { step: "7", actor: "RPA",       action: "キューから取り出し、弥生販売 26 を自動操作して仕入伝票を登録（ステップ毎にログ記録）" },
  { step: "8", actor: "RPA",       action: "登録成功 → 弥生販売からCSVエクスポート → SQLite マスタを即時再同期" },
  { step: "!", actor: "RPA失敗時", action: "PC画面にアラート表示。管理画面の「再実行」ボタンから手動リトライ可能（送信済みフラグで二重登録防止）" },
];

const FLOW_UNKNOWN = [
  { step: "A", actor: "サーバー",  action: "JANコードが商品マスタに存在しないと判定" },
  { step: "B", actor: "サーバー",  action: "楽天ウェブサービスAPI へ JAN コードで検索" },
  { step: "C", actor: "サーバー",  action: "未発見の場合は Open Food Facts API にフォールバック" },
  { step: "D", actor: "アプリ",    action: "取得した商品名（または空欄）をスタッフに提示" },
  { step: "E", actor: "スタッフ",  action: "商品名・仕入単価・仕入先を確認 / 修正して入力" },
  { step: "F", actor: "RPA",       action: "伝票登録と同時に弥生販売の商品マスタに新規商品を自動登録" },
  { step: "G", actor: "RPA",       action: "弥生販売からCSV再エクスポート → SQLite マスタを即時反映" },
];

const PHASES = [
  {
    phase: "Phase 1",
    title: "PCサーバー構築",
    pills: ["Python", "FastAPI", "SQLite"],
    items: [
      "FastAPI サーバーのセットアップ",
      "弥生販売 CSVエクスポート → SQLite マスタDB作成",
      "楽天 API 開発者登録・APIキー取得",
      "JANコード照合ロジック実装",
      "仕入伝票CSV生成ロジック実装",
      "PINコード認証ミドルウェア実装",
      "GET /health エンドポイント（弥生販売起動確認含む）",
    ],
  },
  {
    phase: "Phase 2",
    title: "RPA実装",
    pills: ["pywinauto", "弥生販売 26"],
    items: [
      "弥生販売 26 バージョン確認ロジック（起動時チェック）",
      "弥生販売への仕入伝票インポートの自動化",
      "弥生販売への新規商品マスタ登録の自動化",
      "asyncio.Queue によるRPA排他制御キュー実装",
      "処理ステップのSQLiteログ記録",
      "失敗時のPC画面アラート + 手動再実行UI",
      "RPA完了後のCSV再エクスポート・マスタ再同期",
    ],
  },
  {
    phase: "Phase 3",
    title: "Flutterアプリ実装",
    pills: ["Flutter", "mobile_scanner"],
    items: [
      "初回設定画面（サーバーIP + PIN入力）",
      "GET /health で起動時にサーバー疎通確認",
      "JANコードスキャン機能（mobile_scanner）",
      "スキャン → 数量入力 → 商品確認の画面フロー",
      "セッション方式マルチユーザー対応（参加・離脱）",
      "30分タイムアウト検知 + 下書き保存・復元",
      "RPAキュー待機中の待機件数表示",
      "不明JAN: 外部API取得 + 手動入力フォーム",
    ],
  },
  {
    phase: "Phase 4",
    title: "結合テスト・運用",
    pills: ["テスト", "運用"],
    items: [
      "PC + USB バーコードリーダー統合テスト",
      "弥生販売 26 への実データ連携テスト",
      "RPA失敗シナリオ・手動再実行テスト",
      "同時複数伝票確定（キュー動作）テスト",
      "セッションタイムアウト・下書き復元テスト",
      "スタッフへの操作説明・マニュアル作成",
    ],
  },
];

// ─── Architecture SVG ────────────────────────────────────────────────────────

function ArchDiagram() {
  const theme = useHostTheme();
  const fg      = theme.text.primary;
  const muted   = theme.text.tertiary;
  const border  = theme.stroke.secondary;
  const accent  = theme.accent.primary;
  const surface = theme.bg.elevated;

  const BOX_R = 6;
  type Box = { id: string; x: number; y: number; w: number; h: number; label: string; sub?: string; highlight?: boolean };
  const boxes: Box[] = [
    { id: "flutter", x: 20,  y: 20,  w: 130, h: 54, label: "Flutter App",       sub: "Android / iOS" },
    { id: "usb",     x: 20,  y: 100, w: 130, h: 54, label: "PC + USB",          sub: "バーコードリーダー" },
    { id: "server",  x: 215, y: 60,  w: 150, h: 54, label: "Python FastAPI",    sub: "PCサーバー",     highlight: true },
    { id: "db",      x: 440, y: 5,   w: 140, h: 54, label: "SQLite",            sub: "商品マスタDB" },
    { id: "rpa",     x: 440, y: 75,  w: 140, h: 54, label: "pywinauto RPA",     sub: "RPAエンジン",    highlight: true },
    { id: "ext",     x: 440, y: 145, w: 140, h: 54, label: "楽天 / OFF API",    sub: "外部JAN検索" },
    { id: "yayoi",   x: 660, y: 75,  w: 140, h: 54, label: "弥生販売",          sub: "デスクトップ",   highlight: true },
  ];

  type Arrow = { x1: number; y1: number; x2: number; y2: number; label: string; dashed?: boolean };
  const arrows: Arrow[] = [
    { x1: 150, y1: 47,  x2: 215, y2: 87,  label: "JANコード (Wi-Fi)" },
    { x1: 150, y1: 127, x2: 215, y2: 107, label: "JANコード (USB)" },
    { x1: 365, y1: 78,  x2: 440, y2: 32,  label: "商品照合" },
    { x1: 365, y1: 87,  x2: 440, y2: 102, label: "伝票データ" },
    { x1: 365, y1: 96,  x2: 440, y2: 172, label: "不明JAN検索", dashed: true },
    { x1: 580, y1: 102, x2: 660, y2: 102, label: "UI自動操作" },
    { x1: 730, y1: 75,  x2: 580, y2: 32,  label: "CSV再エクスポート", dashed: true },
  ];

  return (
    <svg viewBox="0 0 840 220" width="100%" style={{ display: "block" }}>
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill={muted} />
        </marker>
      </defs>

      {arrows.map((a, i) => (
        <g key={i}>
          <line
            x1={a.x1} y1={a.y1} x2={a.x2} y2={a.y2}
            stroke={muted} strokeWidth={1.5}
            strokeDasharray={a.dashed ? "5,3" : undefined}
            markerEnd="url(#arrowhead)"
          />
          <text
            x={(a.x1 + a.x2) / 2 + (a.dashed ? 4 : 0)}
            y={(a.y1 + a.y2) / 2 - 5}
            fill={muted} fontSize={9} textAnchor="middle"
            fontFamily="system-ui, sans-serif"
          >{a.label}</text>
        </g>
      ))}

      {boxes.map((b) => (
        <g key={b.id}>
          <rect
            x={b.x} y={b.y} width={b.w} height={b.h}
            rx={BOX_R} ry={BOX_R}
            fill={surface}
            stroke={b.highlight ? accent : border}
            strokeWidth={b.highlight ? 1.5 : 1}
          />
          <text
            x={b.x + b.w / 2} y={b.y + 22}
            fill={b.highlight ? accent : fg}
            fontSize={11} fontWeight={b.highlight ? "600" : "400"}
            textAnchor="middle" fontFamily="system-ui, sans-serif"
          >{b.label}</text>
          {b.sub && (
            <text
              x={b.x + b.w / 2} y={b.y + 38}
              fill={muted} fontSize={9} textAnchor="middle"
              fontFamily="system-ui, sans-serif"
            >{b.sub}</text>
          )}
        </g>
      ))}

      {/* Legend */}
      <g transform="translate(20, 195)">
        <line x1={0} y1={5} x2={22} y2={5} stroke={muted} strokeWidth={1.5} markerEnd="url(#arrowhead)" />
        <text x={26} y={9} fill={muted} fontSize={9} fontFamily="system-ui, sans-serif">通常フロー</text>
        <line x1={95} y1={5} x2={117} y2={5} stroke={muted} strokeWidth={1.5} strokeDasharray="5,3" markerEnd="url(#arrowhead)" />
        <text x={121} y={9} fill={muted} fontSize={9} fontFamily="system-ui, sans-serif">不明JAN時のみ</text>
        <rect x={210} y={0} width={10} height={10} rx={2} fill={surface} stroke={accent} strokeWidth={1.5} />
        <text x={224} y={9} fill={muted} fontSize={9} fontFamily="system-ui, sans-serif">主要コンポーネント</text>
      </g>
    </svg>
  );
}

// ─── Flow Step ───────────────────────────────────────────────────────────────

function FlowStep({ step, actor, action }: { step: string; actor: string; action: string }) {
  const theme = useHostTheme();
  const circleStyle: CSSProperties = {
    minWidth: 24, height: 24, borderRadius: "50%",
    background: theme.bg.elevated,
    border: `1px solid ${theme.stroke.secondary}`,
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 11, fontWeight: 600, color: theme.accent.primary, flexShrink: 0,
  };
  return (
    <Row gap={12} style={{ alignItems: "flex-start", padding: "5px 0" }}>
      <div style={circleStyle}>{step}</div>
      <div>
        <Text tone="tertiary" size="small">{actor}</Text>
        <Text>{action}</Text>
      </div>
    </Row>
  );
}

// ─── Phase Card ──────────────────────────────────────────────────────────────

function PhaseCard({ phase, title, pills, items }: typeof PHASES[0]) {
  return (
    <Card>
      <CardHeader trailing={
        <Row gap={4}>
          {pills.map((p) => <Pill key={p} size="sm">{p}</Pill>)}
        </Row>
      }>
        {phase} — {title}
      </CardHeader>
      <CardBody>
        <Stack gap={6}>
          {items.map((item, i) => (
            <Row key={i} gap={8} style={{ alignItems: "flex-start" }}>
              <Text tone="tertiary" size="small" style={{ flexShrink: 0 }}>{i + 1}.</Text>
              <Text size="small">{item}</Text>
            </Row>
          ))}
        </Stack>
      </CardBody>
    </Card>
  );
}

// ─── Main Canvas ─────────────────────────────────────────────────────────────

export default function JanScannerDesign() {
  return (
    <Stack style={{ padding: 32, maxWidth: 1100, margin: "0 auto", gap: 28 }}>

      {/* Header */}
      <div>
        <H1>JANスキャナー 仕入管理システム</H1>
        <Text tone="secondary">
          システム設計書 — 弥生販売連携 / Flutter ネイティブアプリ / Python RPA 構成
        </Text>
      </div>

      {/* Stats */}
      <Row gap={20} wrap>
        <Stat label="スキャン端末"   value="Flutter + PC" />
        <Stat label="連携システム"   value="弥生販売" />
        <Stat label="自動化エンジン" value="pywinauto" />
        <Stat label="外部JAN検索"    value="楽天 + OFF" />
        <Stat label="在庫の正者"     value="弥生販売のみ" />
      </Row>

      <Divider />

      {/* Architecture */}
      <div>
        <H2>システムアーキテクチャ</H2>
        <Spacer />
        <Card variant="borderless">
          <CardBody>
            <ArchDiagram />
          </CardBody>
        </Card>
      </div>

      <Divider />

      {/* Tech Stack + Decisions */}
      <Grid columns={2} gap={24}>
        <div>
          <H2>技術スタック</H2>
          <Table
            headers={TECH_STACK_HEADERS}
            rows={TECH_STACK_ROWS}
            striped
          />
        </div>
        <div>
          <H2>主要設計決定</H2>
          <Table
            headers={DECISIONS_HEADERS}
            rows={DECISIONS_ROWS}
            striped
          />
        </div>
      </Grid>

      <Divider />

      {/* Data flows */}
      <Grid columns={2} gap={24}>
        <div>
          <H2>データフロー — 通常スキャン</H2>
          <Stack gap={0}>
            {FLOW_NORMAL.map((f) => (
              <FlowStep key={f.step} {...f} />
            ))}
          </Stack>
        </div>

        <div>
          <H2>不明JANコード処理フロー</H2>
          <Callout tone="warning" title="不明JAN発生時の追加ステップ">
            通常フローのステップ3で商品が見つからなかった場合に実行されます。
            入荷作業は停止せず、外部APIが商品名を自動補完します。
          </Callout>
          <Stack gap={0} style={{ marginTop: 12 }}>
            {FLOW_UNKNOWN.map((f) => (
              <FlowStep key={f.step} {...f} />
            ))}
          </Stack>
        </div>
      </Grid>

      <Divider />

      {/* Non-functional requirements */}
      <div>
        <H2>非機能要件・運用仕様</H2>
        <Table
          headers={NFR_HEADERS}
          rows={NFR_ROWS}
          striped
        />
      </div>

      <Divider />

      {/* Implementation Phases */}
      <div>
        <H2>実装フェーズ</H2>
        <Grid columns={2} gap={16} style={{ marginTop: 12 }}>
          {PHASES.map((p) => (
            <PhaseCard key={p.phase} {...p} />
          ))}
        </Grid>
      </div>

    </Stack>
  );
}
