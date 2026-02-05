//
//  Exercise.swift
//  workout tracker app
//
//  Created by Claude on 25.01.2026.
//

import Foundation

/// Exercise model within a workout
struct Exercise: Codable, Identifiable, Equatable {
    let id: UUID
    var workoutId: UUID
    var name: String
    var exerciseOrder: Int
    var notes: String?
    let createdAt: Date

    // Related data (not stored in DB, loaded separately)
    var sets: [WorkoutSet]?

    enum CodingKeys: String, CodingKey {
        case id
        case workoutId = "workout_id"
        case name
        case exerciseOrder = "exercise_order"
        case notes
        case createdAt = "created_at"
    }

    // Custom init for creating new exercises
    init(
        id: UUID = UUID(),
        workoutId: UUID,
        name: String,
        exerciseOrder: Int,
        notes: String? = nil,
        sets: [WorkoutSet]? = nil
    ) {
        self.id = id
        self.workoutId = workoutId
        self.name = name
        self.exerciseOrder = exerciseOrder
        self.notes = notes
        self.createdAt = Date()
        self.sets = sets
    }

    // Decoder init
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        workoutId = try container.decode(UUID.self, forKey: .workoutId)
        name = try container.decode(String.self, forKey: .name)
        exerciseOrder = try container.decode(Int.self, forKey: .exerciseOrder)
        notes = try container.decodeIfPresent(String.self, forKey: .notes)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        sets = nil // Loaded separately
    }

    // Encoder
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(workoutId, forKey: .workoutId)
        try container.encode(name, forKey: .name)
        try container.encode(exerciseOrder, forKey: .exerciseOrder)
        try container.encodeIfPresent(notes, forKey: .notes)
        try container.encode(createdAt, forKey: .createdAt)
    }
}

// MARK: - Helper Properties
extension Exercise {
    /// Total number of sets for this exercise
    var setCount: Int {
        sets?.count ?? 0
    }

    /// Total number of reps across all sets
    var totalReps: Int {
        sets?.reduce(0) { $0 + $1.reps } ?? 0
    }

    /// Average RPE across all sets (if available)
    var averageRPE: Double? {
        guard let sets = sets, !sets.isEmpty else { return nil }
        let rpeValues = sets.compactMap { $0.rpe }
        guard !rpeValues.isEmpty else { return nil }
        return Double(rpeValues.reduce(0, +)) / Double(rpeValues.count)
    }
}
