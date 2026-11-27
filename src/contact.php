<?php
/**
 * Contact form handler: the only dynamic file on the site (FR-07, NFR-05).
 *
 * POST only. Validates on the server, rate-limits by a salted hash of the
 * client address, and appends one JSON line to data/messages.jsonl.
 * No cookies, no sessions, no database, no mail, no secrets.
 *
 * Answers with JSON {ok, error} when the request has "Accept: application/json",
 * otherwise with a minimal localised HTML page (plain form post without JavaScript).
 */

declare(strict_types=1);

const LANGS = ['kk', 'ru', 'en'];
const DEFAULT_LANG = 'en';
const RATE_SECONDS = 30;
const MAX_BODY_BYTES = 32768;
const NAME_MIN = 2;
const NAME_MAX = 80;
const CONTACT_MAX = 120;
const MESSAGE_MIN = 10;
const MESSAGE_MAX = 2000;
const GITHUB_URL = 'https://github.com/merelymerey';

/** Texts for the no-JavaScript result page. Keep in step with content/<lang>.json. */
const TEXT = [
    'en' => [
        'title_ok' => 'Message sent',
        'title_fail' => 'Message not sent',
        'ok' => 'Thank you, your message has been saved. I will read it soon.',
        'invalid' => 'Please check the form: the name must be 2 to 80 characters, the reply contact up to 120 and the message 10 to 2000 characters.',
        'rate' => 'Too many messages in a short time. Please wait half a minute and try again.',
        'method' => 'This address only accepts messages sent from the contact form.',
        'server' => 'The message could not be sent and was not saved. Please try again later or reach me through GitHub:',
        'back' => 'Back to the contact page',
    ],
    'ru' => [
        'title_ok' => 'Сообщение отправлено',
        'title_fail' => 'Сообщение не отправлено',
        'ok' => 'Спасибо, сообщение сохранено. Скоро его прочитаю.',
        'invalid' => 'Проверьте форму: имя должно быть от 2 до 80 символов, контакт для ответа до 120, сообщение от 10 до 2000 символов.',
        'rate' => 'Слишком много сообщений за короткое время. Подождите полминуты и попробуйте снова.',
        'method' => 'Этот адрес принимает только сообщения, отправленные из формы обратной связи.',
        'server' => 'Сообщение не удалось отправить, оно не сохранено. Попробуйте позже или напишите мне через GitHub:',
        'back' => 'Вернуться на страницу контактов',
    ],
    'kk' => [
        'title_ok' => 'Хабарлама жіберілді',
        'title_fail' => 'Хабарлама жіберілмеді',
        'ok' => 'Рақмет, хабарламаңыз сақталды. Жақын арада оқимын.',
        'invalid' => 'Форманы тексеріңіз: ат 2-ден 80 таңбаға дейін, жауап беруге арналған байланыс 120 таңбаға дейін, хабарлама 10-нан 2000 таңбаға дейін болуы керек.',
        'rate' => 'Қысқа уақыт ішінде тым көп хабарлама жіберілді. Жарты минут күтіп, қайталап көріңіз.',
        'method' => 'Бұл мекенжай тек байланыс формасынан жіберілген хабарламаларды қабылдайды.',
        'server' => 'Хабарлама жіберілмеді және сақталмады. Кейінірек қайталап көріңіз немесе маған GitHub арқылы жазыңыз:',
        'back' => 'Байланыс бетіне оралу',
    ],
];

function h(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function text_length(string $value): int
{
    if (function_exists('mb_strlen')) {
        return mb_strlen($value, 'UTF-8');
    }
    return (int) preg_match_all('/./us', $value);
}

/**
 * Returns the trimmed, normalised field value, or null when the input is not
 * a valid UTF-8 string.
 */
function clean_field($value, bool $multiline): ?string
{
    if (!is_string($value) || preg_match('//u', $value) !== 1) {
        return null;
    }
    $value = str_replace(["\r\n", "\r"], "\n", $value);
    if ($multiline) {
        $value = preg_replace('/[^\P{Cc}\n\t]+/u', '', $value);
    } else {
        $value = preg_replace('/\p{Cc}+/u', ' ', $value);
    }
    if (!is_string($value)) {
        return null;
    }
    $value = preg_replace('/^\s+|\s+$/u', '', $value);
    return is_string($value) ? $value : null;
}

function wants_json(): bool
{
    $accept = isset($_SERVER['HTTP_ACCEPT']) ? (string) $_SERVER['HTTP_ACCEPT'] : '';
    return stripos($accept, 'application/json') !== false;
}

/** Sends the response and ends the script. $error is null on success. */
function respond(int $status, ?string $error, string $lang): void
{
    http_response_code($status);
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: no-referrer');

    if (wants_json()) {
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode(['ok' => $error === null, 'error' => $error]);
        exit;
    }

    $text = TEXT[$lang];
    $withLink = false;
    if ($error === null) {
        $message = $text['ok'];
    } elseif ($status === 429) {
        $message = $text['rate'];
    } elseif ($status === 405) {
        $message = $text['method'];
    } elseif ($status === 400) {
        $message = $text['invalid'];
    } else {
        $message = $text['server'];
        $withLink = true;
    }
    $title = $error === null ? $text['title_ok'] : $text['title_fail'];
    $link = $withLink
        ? ' <a href="' . h(GITHUB_URL) . '" rel="noopener noreferrer">' . h(GITHUB_URL) . '</a>'
        : '';

    header('Content-Type: text/html; charset=UTF-8');
    echo '<!DOCTYPE html>' . "\n"
        . '<html lang="' . h($lang) . '">' . "\n"
        . '<head>' . "\n"
        . '<meta charset="utf-8">' . "\n"
        . '<meta name="viewport" content="width=device-width, initial-scale=1">' . "\n"
        . '<meta name="robots" content="noindex">' . "\n"
        . '<meta name="color-scheme" content="light dark">' . "\n"
        . '<title>' . h($title) . '</title>' . "\n"
        . '<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">' . "\n"
        . '<link rel="stylesheet" href="/assets/css/style.css">' . "\n"
        . '</head>' . "\n"
        . '<body class="plain-page">' . "\n"
        . '<main id="main" class="container">' . "\n"
        . '<h1>' . h($title) . '</h1>' . "\n"
        . '<p>' . h($message) . $link . '</p>' . "\n"
        . '<p><a href="/' . h($lang) . '/contact.html">' . h($text['back']) . '</a></p>' . "\n"
        . '</main>' . "\n"
        . '</body>' . "\n"
        . '</html>' . "\n";
    exit;
}

/** Makes sure the data directory exists, is writable and is closed to the web. */
function ensure_data_dir(string $dir): bool
{
    if (!is_dir($dir) && !@mkdir($dir, 0700, true) && !is_dir($dir)) {
        return false;
    }
    $guard = $dir . '/.htaccess';
    if (!is_file($guard)) {
        $rules = "<IfModule mod_authz_core.c>\n  Require all denied\n</IfModule>\n"
            . "<IfModule !mod_authz_core.c>\n  Order allow,deny\n  Deny from all\n</IfModule>\n";
        if (@file_put_contents($guard, $rules, LOCK_EX) === false) {
            return false;
        }
    }
    return is_writable($dir);
}

/**
 * One accepted request per client address per RATE_SECONDS.
 * The address is stored only as a salted SHA-256 hash; the salt is random,
 * created on the host on first use, and old entries are dropped on every call.
 * Returns true when limited, false when allowed, null when the file cannot be used.
 */
function rate_limited(string $dir, int $now): ?bool
{
    $handle = @fopen($dir . '/ratelimit.json', 'c+');
    if ($handle === false) {
        return null;
    }
    if (!flock($handle, LOCK_EX)) {
        fclose($handle);
        return null;
    }

    $raw = stream_get_contents($handle);
    $state = json_decode(is_string($raw) ? $raw : '', true);
    if (
        !is_array($state)
        || !isset($state['salt'], $state['hits'])
        || !is_string($state['salt'])
        || !is_array($state['hits'])
    ) {
        try {
            $salt = bin2hex(random_bytes(16));
        } catch (Exception $exception) {
            flock($handle, LOCK_UN);
            fclose($handle);
            return null;
        }
        $state = ['salt' => $salt, 'hits' => []];
    }

    $address = isset($_SERVER['REMOTE_ADDR']) ? (string) $_SERVER['REMOTE_ADDR'] : 'unknown';
    $key = hash('sha256', $state['salt'] . '|' . $address);

    $hits = [];
    foreach ($state['hits'] as $entry => $time) {
        if (is_int($time) && $time <= $now && $now - $time < RATE_SECONDS) {
            $hits[(string) $entry] = $time;
        }
    }
    $limited = isset($hits[$key]);
    if (!$limited) {
        $hits[$key] = $now;
    }

    $json = json_encode(['salt' => $state['salt'], 'hits' => (object) $hits]);
    $written = is_string($json)
        && ftruncate($handle, 0)
        && rewind($handle)
        && fwrite($handle, $json) === strlen($json);
    fflush($handle);
    flock($handle, LOCK_UN);
    fclose($handle);

    return $written ? $limited : null;
}

function store_message(string $dir, array $record): bool
{
    $line = json_encode($record, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if (!is_string($line)) {
        return false;
    }
    $line .= "\n";
    $bytes = @file_put_contents($dir . '/messages.jsonl', $line, FILE_APPEND | LOCK_EX);
    return $bytes === strlen($line);
}

/* ------------------------------------------------------------------ request */

$lang = DEFAULT_LANG;
if (isset($_POST['lang']) && is_string($_POST['lang']) && in_array($_POST['lang'], LANGS, true)) {
    $lang = $_POST['lang'];
}

$method = isset($_SERVER['REQUEST_METHOD']) ? (string) $_SERVER['REQUEST_METHOD'] : '';
if ($method !== 'POST') {
    header('Allow: POST');
    respond(405, 'method_not_allowed', $lang);
}

$bodyBytes = isset($_SERVER['CONTENT_LENGTH']) ? (int) $_SERVER['CONTENT_LENGTH'] : 0;
if ($bodyBytes > MAX_BODY_BYTES) {
    respond(400, 'invalid_request', $lang);
}

// Honeypot: real visitors never see or fill this field.
$honeypot = isset($_POST['website']) ? $_POST['website'] : '';
if (!is_string($honeypot) || $honeypot !== '') {
    respond(400, 'invalid_request', $lang);
}

$name = clean_field(isset($_POST['name']) ? $_POST['name'] : '', false);
$contact = clean_field(isset($_POST['contact']) ? $_POST['contact'] : '', false);
$message = clean_field(isset($_POST['message']) ? $_POST['message'] : '', true);

if ($name === null || text_length($name) < NAME_MIN || text_length($name) > NAME_MAX) {
    respond(400, 'invalid_name', $lang);
}
if ($contact === null || text_length($contact) > CONTACT_MAX) {
    respond(400, 'invalid_contact', $lang);
}
if ($message === null || text_length($message) < MESSAGE_MIN || text_length($message) > MESSAGE_MAX) {
    respond(400, 'invalid_message', $lang);
}

$dataDir = __DIR__ . '/data';
if (!ensure_data_dir($dataDir)) {
    respond(500, 'storage_failed', $lang);
}

$now = time();
$limited = rate_limited($dataDir, $now);
if ($limited === null) {
    respond(500, 'storage_failed', $lang);
}
if ($limited) {
    header('Retry-After: ' . RATE_SECONDS);
    respond(429, 'rate_limited', $lang);
}

$record = [
    'time' => gmdate('Y-m-d\TH:i:s\Z', $now),
    'lang' => $lang,
    'name' => $name,
    'contact' => $contact,
    'message' => $message,
];
if (!store_message($dataDir, $record)) {
    respond(500, 'storage_failed', $lang);
}

respond(200, null, $lang);
