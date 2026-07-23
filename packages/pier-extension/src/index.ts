/**
 * Pier Hermes Agent Extension
 *
 * TypeScript companion to the Python plugin — provides client-side
 * tool definitions, UI extensions, and protocol types for the
 * Pi ↔ Hermes integration.
 */

export interface PierExtensionConfig {
  /** Path to the Pi CLI binary or command name */
  piPath: string;
  /** Default Pi model to use for delegated coding tasks */
  defaultModel?: string;
  /** Whether to auto-approve tool use (dangerous — off by default) */
  autoApprove?: boolean;
}

export class PierExtension {
  constructor(public readonly config: PierExtensionConfig) {}

  /** Return the extension's display name */
  get name(): string {
    return "pier";
  }

  /** Return the extension's version */
  get version(): string {
    return "0.1.0";
  }
}
