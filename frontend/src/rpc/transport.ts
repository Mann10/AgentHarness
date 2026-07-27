import { spawn, ChildProcess } from 'child_process';

export type MessageCallback = (line: string) => void;
export type ErrorCallback = (error: Error) => void;
export type CloseCallback = (code: number | null) => void;

export interface TransportOptions {
  command: string;
  args: string[];
  onMessage: MessageCallback;
  onError?: ErrorCallback;
  onClose?: CloseCallback;
  /** Environment variables to pass (default: inherit from parent + PYTHONUNBUFFERED=1) */
  env?: Record<string, string>;
}

export class StdioTransport {
  private _process: ChildProcess | null = null;
  private _buffer = '';
  private _onMessage: MessageCallback;
  private _onError?: ErrorCallback;
  private _onClose?: CloseCallback;

  constructor(private _options: TransportOptions) {
    this._onMessage = _options.onMessage;
    this._onError = _options.onError;
    this._onClose = _options.onClose;
  }

  /** Spawn the Python backend process and start reading stdout */
  async start(): Promise<void> {
    const env = {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      ...this._options.env,
    };

    this._process = spawn(this._options.command, this._options.args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      env,
    });

    // Read stdout line-by-line with buffer for partial reads
    this._process.stdout!.on('data', (chunk: Buffer) => {
      this._buffer += chunk.toString();
      const lines = this._buffer.split('\n');
      this._buffer = lines.pop() ?? ''; // incomplete line stays in buffer
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed) this._onMessage(trimmed);
      }
    });

    // Forward stderr to console.warn (not JSON-RPC — log only)
    this._process.stderr!.on('data', (chunk: Buffer) => {
      console.warn('[backend]', chunk.toString().trimEnd());
    });

    // Handle process exit
    this._process.on('exit', (code) => {
      this._onClose?.(code);
    });

    // Handle process errors
    this._process.on('error', (err) => {
      this._onError?.(err);
    });
  }

  /** Write a JSON-RPC message to stdin */
  send(message: string): void {
    if (this._process?.stdin?.writable) {
      this._process.stdin.write(message + '\n');
    } else {
      this._onError?.(new Error('Transport not connected'));
    }
  }

  /** Gracefully close stdin and kill the subprocess */
  async stop(): Promise<void> {
    if (!this._process) return;

    // Close stdin to signal EOF to Python
    this._process.stdin?.end();

    return new Promise((resolve) => {
      const killTimeout = setTimeout(() => {
        this._process?.kill('SIGTERM');
      }, 5000);

      this._process!.on('exit', () => {
        clearTimeout(killTimeout);
        this._process = null;
        resolve();
      });
    });
  }

  get pid(): number | undefined {
    return this._process?.pid;
  }

  get isRunning(): boolean {
    return this._process !== null && !this._process.killed;
  }
}
