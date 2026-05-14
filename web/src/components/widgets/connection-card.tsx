"use client";

import { useState } from "react";
import { Plug, Unplug, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { labelCommandMode } from "@/lib/types";
import type { ConnectResponse } from "@/lib/types";

interface ConnectionCardProps {
  connected: boolean;
  loading: boolean;
  /** From GET /api/health | /api/state — read-only (actual session on the robot). */
  activeCommandMode?: string | null;
  onConnect: (serialPort: string | null) => Promise<ConnectResponse>;
  onDisconnect: () => Promise<void>;
}

export function ConnectionCard({
  connected,
  loading,
  activeCommandMode,
  onConnect,
  onDisconnect,
}: ConnectionCardProps) {
  const [serialPort, setSerialPort] = useState("");

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Plug className="size-3.5 text-muted-foreground" />
          Connection
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {connected && activeCommandMode ? (
          <p className="text-[11px] text-muted-foreground">
            Session on device:{" "}
            <span className="font-medium text-foreground">
              {labelCommandMode(activeCommandMode)}
            </span>
            {" "}
            — change mode in the dock, then disconnect and connect again to apply.
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          <Input
            value={serialPort}
            onChange={(e) => setSerialPort(e.target.value)}
            placeholder="Serial port (optional), e.g. /dev/ttyUSB0"
            className="min-w-[200px] flex-1"
            disabled={connected}
          />

          {!connected ? (
            <Button size="sm" disabled={loading} onClick={() => void onConnect(serialPort.trim() || null)}>
              {loading ? <Loader2 className="size-3.5 animate-spin" /> : <Plug className="size-3.5" />}
              Connect
            </Button>
          ) : null}

          {connected ? (
            <Button variant="outline" size="sm" disabled={loading} onClick={() => void onDisconnect()}>
              <Unplug className="size-3.5" />
              Disconnect
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
