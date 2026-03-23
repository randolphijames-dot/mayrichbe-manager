import dayjs from 'dayjs'

export function getTzOffset(): number {
  const v = localStorage.getItem('sm_tz_offset')
  return v !== null ? Number(v) : 9  // 默认 +9 JST
}

export function setTzOffset(offset: number) {
  localStorage.setItem('sm_tz_offset', String(offset))
}

// 用于 created_at / updated_at 等真正的 UTC 字段
export function fmtUtc(d: string, fmt = 'MM-DD HH:mm'): string {
  return dayjs(d).add(getTzOffset(), 'hour').format(fmt)
}

// 用于 scheduled_at（前端用户输入的时间，后端按+8处理存储）
export function fmtScheduled(d: string, fmt = 'MM-DD HH:mm'): string {
  return dayjs(d).add(getTzOffset() - 8, 'hour').format(fmt)
}

// 创建任务前，将用户选择的时间转换为后端期望的格式（+8基准）
export function toBackendScheduled(localTimeStr: string): string {
  const adj = getTzOffset() - 8
  return dayjs(localTimeStr).subtract(adj, 'hour').format('YYYY-MM-DDTHH:mm')
}
