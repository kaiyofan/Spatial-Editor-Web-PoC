declare module '@mkkellogg/gaussian-splats-3d' {
    export const SceneFormat: {
        Splat: 0;
        KSplat: 1;
        Ply: 2;
        Spz: 3;
    };
    export class Viewer {
        constructor(options?: any);
        addSplatScene(url: string, options?: any): Promise<void>;
        start(): void;
        update(): void;
        dispose(): void;
        camera?: any;
        controls?: any;
    }
    export class DropInViewer extends Viewer { }
}
