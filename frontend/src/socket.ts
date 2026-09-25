import { io, Socket } from "socket.io-client";
// @ts-ignore
import { socketio_port } from "../../../../sites/common_site_config.json";

let socket: Socket | null = null;
export function initSocket(): Socket | null {
  const siteName = (window as Window & { site_name?: string }).site_name;
  const sessionUser = (window as any).frappe?.session?.user || (window as any).frappe?.boot?.user?.name;

  // Don't initialize socket on public submission pages without site context or as Guest
  if (!siteName || sessionUser === "Guest") {
    return null;
  }

  const host = window.location.hostname;
  const port = window.location.port ? `:${socketio_port}` : "";
  const protocol = port ? "http" : "https";
  const url = `${protocol}://${host}${port}/${siteName}`;

  try {
    socket = io(url, {
      withCredentials: true,
      reconnectionAttempts: 2,
    });
  } catch {
    socket = null;
  }
  return socket;
}

export function useSocket(): Socket | null {
  return socket;
}
