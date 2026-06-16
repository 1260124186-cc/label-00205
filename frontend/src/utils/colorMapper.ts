/**
 * 颜色映射工具
 *
 * 将预测状态、健康度指数(HI)、风险等级映射为可视化颜色。
 * 与后端 color_mapper.py 保持一致的配色方案。
 */

export type VisualizationMode = 'status' | 'hi' | 'risk';

export enum StatusCode {
  NORMAL = 0,
  ATTENTION = 1,
  WARNING = 2,
  CRITICAL = 3,
  FAULT = 4,
}

export const StatusCodeMap: Record<number, string> = {
  0: '正常',
  1: '关注级预警',
  2: '检查级预警',
  3: '紧急级预警',
  4: '故障',
};

export const StatusColorMap: Record<number, string> = {
  0: '#4CAF50',
  1: '#FFC107',
  2: '#FF9800',
  3: '#F44336',
  4: '#9C27B0',
};

export const RiskLevelMap: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  critical: '极高风险',
};

export const RiskColorMap: Record<string, string> = {
  low: '#4CAF50',
  medium: '#FFC107',
  high: '#FF5722',
  critical: '#F44336',
};

export interface BoltStatusData {
  bolt_id: string;
  status_code?: number;
  status?: string;
  hi_score?: number;
  hi_level?: string;
  risk_level?: string;
  risk_score?: number;
  confidence?: number;
  diagnosis?: string;
  recommendations?: string[];
  [key: string]: any;
}

export class ColorMapper {
  private statusColors: Record<number, [number, number, number]> = {
    0: [76, 175, 80],
    1: [255, 193, 7],
    2: [255, 152, 0],
    3: [244, 67, 54],
    4: [156, 39, 176],
  };

  private riskColors: Record<string, [number, number, number]> = {
    low: [76, 175, 80],
    medium: [255, 193, 7],
    high: [255, 87, 34],
    critical: [244, 67, 54],
  };

  private hiGradientStops: Array<[number, [number, number, number]]> = [
    [0.0, [244, 67, 54]],
    [0.3, [255, 152, 0]],
    [0.5, [255, 193, 7]],
    [0.7, [139, 195, 74]],
    [1.0, [76, 175, 80]],
  ];

  getStatusColor(statusCode: number): [number, number, number] {
    return this.statusColors[statusCode] || this.statusColors[0];
  }

  getHiColor(hiScore: number): [number, number, number] {
    const t = Math.max(0, Math.min(100, hiScore)) / 100;

    for (let i = 0; i < this.hiGradientStops.length - 1; i++) {
      const [t0, c0] = this.hiGradientStops[i];
      const [t1, c1] = this.hiGradientStops[i + 1];
      if (t0 <= t && t <= t1) {
        const ratio = t1 !== t0 ? (t - t0) / (t1 - t0) : 0;
        const r = Math.round(c0[0] + (c1[0] - c0[0]) * ratio);
        const g = Math.round(c0[1] + (c1[1] - c0[1]) * ratio);
        const b = Math.round(c0[2] + (c1[2] - c0[2]) * ratio);
        return [r, g, b];
      }
    }

    return this.hiGradientStops[this.hiGradientStops.length - 1][1];
  }

  getRiskColor(riskLevel: string): [number, number, number] {
    return this.riskColors[riskLevel] || this.riskColors['low'];
  }

  getRiskScoreColor(riskScore: number): [number, number, number] {
    const score = Math.max(1, Math.min(10, riskScore));
    const t = (score - 1) / 9;
    const r = Math.round(76 + (244 - 76) * t);
    const g = Math.round(175 - (175 - 67) * t);
    const b = Math.round(80 - (80 - 54) * t);
    return [r, g, b];
  }

  getColor(mode: VisualizationMode, boltData: BoltStatusData): [number, number, number] {
    switch (mode) {
      case 'status':
        return this.getStatusColor(boltData.status_code || 0);
      case 'hi':
        return this.getHiColor(boltData.hi_score ?? 100);
      case 'risk':
        if (boltData.risk_level) {
          return this.getRiskColor(boltData.risk_level);
        }
        return this.getRiskScoreColor(boltData.risk_score || 1);
      default:
        return this.getStatusColor(0);
    }
  }

  rgbToHex(rgb: [number, number, number]): string {
    return `#${rgb[0].toString(16).padStart(2, '0')}${rgb[1].toString(16).padStart(2, '0')}${rgb[2].toString(16).padStart(2, '0')}`;
  }

  rgbToNormalized(rgb: [number, number, number]): [number, number, number] {
    return [rgb[0] / 255, rgb[1] / 255, rgb[2] / 255];
  }
}

export const colorMapper = new ColorMapper();
