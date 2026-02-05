//
//  Workout.swift
//  workout tracker app
//
//  Created by Claude on 25.01.2026.
//

import Foundation

/// Workout session model
struct Workout: Codable, Identifiable, Equatable {
    let id: UUID
    let userId: UUID
    let date: Date
    var notes: String?
    var duration: Int? // Duration in minutes
    let createdAt: Date
    let updatedAt: Date

    // Related data (not stored in DB, loaded separately)
    var exercises: [Exercise]?

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case date
        case notes
        case duration
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    // Custom init for creating new workouts
    init(
        id: UUID = UUID(),
        userId: UUID,
        date: Date = Date(),
        notes: String? = nil,
        duration: Int? = nil,
        exercises: [Exercise]? = nil
    ) {
        self.id = id
        self.userId = userId
        self.date = date
        self.notes = notes
        self.duration = duration
        self.createdAt = Date()
        self.updatedAt = Date()
        self.exercises = exercises
    }

    // Decoder init
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        userId = try container.decode(UUID.self, forKey: .userId)
        date = try container.decode(Date.self, forKey: .date)
        notes = try container.decodeIfPresent(String.self, forKey: .notes)
        duration = try container.decodeIfPresent(Int.self, forKey: .duration)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        updatedAt = try container.decode(Date.self, forKey: .updatedAt)
        exercises = nil // Loaded separately
    }

    // Encoder
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(userId, forKey: .userId)
        try container.encode(date, forKey: .date)
        try container.encodeIfPresent(notes, forKey: .notes)
        try container.encodeIfPresent(duration, forKey: .duration)
        try container.encode(createdAt, forKey: .createdAt)
        try container.encode(updatedAt, forKey: .updatedAt)
    }
}

// MARK: - Helper Properties
extension Workout {
    /// Total number of exercises in this workout
    var exerciseCount: Int {
        exercises?.count ?? 0
    }

    /// Total number of sets across all exercises
    var totalSets: Int {
        exercises?.reduce(0) { $0 + ($1.sets?.count ?? 0) } ?? 0
    }

    /// Formatted date string
    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    /// Formatted duration string
    var formattedDuration: String {
        guard let duration = duration else { return "—" }

        let hours = duration / 60
        let minutes = duration % 60

        if hours > 0 {
            return "\(hours)h \(minutes)m"
        } else {
            return "\(minutes)m"
        }
    }
}
