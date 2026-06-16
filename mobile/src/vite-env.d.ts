/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'html5-qrcode' {
  export class Html5Qrcode {
    constructor(elementId: string, verbose?: boolean)
    start(
      cameraIdOrConfig: any,
      configuration: any,
      qrCodeSuccessCallback: (decodedText: string, decodedResult?: any) => void,
      qrCodeErrorCallback?: (errorMessage: string) => void
    ): Promise<void>
    stop(): Promise<void>
    scanFile(imageFile: string, showImage?: boolean): Promise<string>
    getRunningTrackCameraCapabilities(): any
    applyVideoConstraints(constraints: any): Promise<void>
    isScanning: boolean
  }
}
