'use client'

import { useState, useEffect } from 'react'
import { RefreshCw, TrendingUp, Download, Upload, CheckCircle, XCircle, Clock, Video, Zap } from 'lucide-react'
import { api } from '@/lib/api'

interface DiscoveryItem {
  id: string
  youtube_url: string
  youtube_video_id: string
  niche: string
  status: string
  view_count: number
  duration_seconds: number
  discovered_at: string
  processed_at: string | null
  error_message: string | null
}

interface FactoryStats {
  total_discovered: number
  total_processed: number
  total_clips: number
  pending_count: number
  processing_count: number
  failed_count: number
  niches: { [key: string]: number }
}

interface SchedulerStatus {
  running: boolean
  jobs: Array<{
    id: string
    name: string
    next_run: string | null
  }>
}

export default function FactoryDashboard() {
  const [discoveries, setDiscoveries] = useState<DiscoveryItem[]>([])
  const [stats, setStats] = useState<FactoryStats | null>(null)
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchDashboardData = async () => {
    try {
      const [discoveriesRes, statsRes, schedulerRes] = await Promise.all([
        api.get('/factory/discoveries?limit=20'),
        api.get('/factory/stats'),
        api.get('/factory/scheduler-status'),
      ])

      setDiscoveries(discoveriesRes.data.discoveries || [])
      setStats(statsRes.data)
      setSchedulerStatus(schedulerRes.data)
    } catch {
      // silently retry on next interval
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboardData()

    if (autoRefresh) {
      const interval = setInterval(fetchDashboardData, 10000) // Refresh every 10s
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed':
      case 'skipped':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'pending':
        return <Clock className="w-5 h-5 text-gray-400" />
      default:
        return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'complete':
        return 'bg-green-100 text-green-800'
      case 'failed':
      case 'skipped':
        return 'bg-red-100 text-red-800'
      case 'pending':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-blue-100 text-blue-800'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Zap className="w-8 h-8 text-yellow-500" />
              AI Factory Status
            </h1>
            <p className="text-gray-600 mt-1">Autonomous content production pipeline</p>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              Auto-refresh
            </label>
            <button
              onClick={fetchDashboardData}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Discovered</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.total_discovered}</p>
                </div>
                <TrendingUp className="w-10 h-10 text-blue-500" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Processed</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.total_processed}</p>
                </div>
                <Video className="w-10 h-10 text-green-500" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Clips Generated</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.total_clips}</p>
                </div>
                <CheckCircle className="w-10 h-10 text-purple-500" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">In Queue</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.pending_count}</p>
                </div>
                <Clock className="w-10 h-10 text-orange-500" />
              </div>
            </div>
          </div>
        )}

        {/* Scheduler Status */}
        {schedulerStatus && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <RefreshCw className={schedulerStatus.running ? 'text-green-500' : 'text-gray-400'} />
              Scheduler Status: {schedulerStatus.running ? 'Running' : 'Stopped'}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {schedulerStatus.jobs.map((job) => (
                <div key={job.id} className="border rounded-lg p-4">
                  <p className="font-semibold text-sm">{job.name}</p>
                  <p className="text-xs text-gray-600 mt-1">
                    Next run: {job.next_run ? new Date(job.next_run).toLocaleString() : 'Not scheduled'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Niche Breakdown */}
        {stats && Object.keys(stats.niches).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-bold mb-4">Niche Breakdown</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(stats.niches).map(([niche, count]) => (
                <div key={niche} className="border rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-blue-600">{count}</p>
                  <p className="text-sm text-gray-600 capitalize">{niche}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Discovery Queue */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <h2 className="text-xl font-bold">Discovery Queue</h2>
            <p className="text-sm text-gray-600 mt-1">Recent videos in the processing pipeline</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Video</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Niche</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Views</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Discovered</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {discoveries.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(item.status)}
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(item.status)}`}>
                          {item.status}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <a
                        href={item.youtube_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-sm"
                      >
                        {item.youtube_video_id}
                      </a>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm capitalize">{item.niche || 'N/A'}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm">{item.view_count?.toLocaleString() || 'N/A'}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm">{Math.floor(item.duration_seconds / 60)}m</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600">
                        {new Date(item.discovered_at).toLocaleDateString()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
