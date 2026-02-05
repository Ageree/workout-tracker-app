//
//  WorkoutSet.swift
//  workout tracker app
//
//  Created by Claude on 25.01.2026.
//

import Foundation

/// Workout set model (individual set for an exercise)
struct WorkoutSet: Codable, Identifiable, Equatable {
    let id: UUID
    var exerciseId: UUID
    var setNumber: Int
    var reps: Int
    var weight: Double? // Weight in kg or lbs
    var rpe: Int? // Rate of Perceived Exertion (1-10)
    var rir: Int? // Reps in Reserve (0+)
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case exerciseId = "exercise_id"
        case setNumber = "set_number"
        case reps
        case weight
        case rpe
        case rir
        case createdAt = "created_at"
    }

    // Custom init for creating new sets
    init(
        id: UUID = UUID(),
        exerciseId: UUID,
        setNumber: Int,
        reps: Int,
        weight: Double? = nil,
        rpe: Int? = nil,
        rir: Int? = nil
    ) {
        self.id = id
        self.exerciseId = exerciseId
        self.setNumber = setNumber
        self.reps = reps
        self.weight = weight
        self.rpe = rpe
        self.rir = rir
        self.createdAt = Date()
    }
}

// MARK: - Helper Properties
extension WorkoutSet {
    /// Formatted weight string (e.g., "80.5 kg")
    func formattedWeight(unit: String = "kg") -> String? {
        guard let weight = weight else { return nil }
        return String(format: "%.1f %@", weight, unit)
    }

    /// RPE indicator (e.g., "8/10")
    var rpeIndicator: String? {
        guard let rpe = rpe else { return nil }
        return "\(rpe)/10"
    }

    /// RIR indicator (e.g., "2 left")
    var rirIndicator: String? {
        guard let rir = rir else { return nil }
        return "\(rir) left"
    }

    /// Validate RPE range (1-10)
    var isValidRPE: Bool {
        guard let rpe = rpe else { return true }
        return rpe >= 1 && rpe <= 10
    }

    /// Validate RIR range (0+)
    var isValidRIR: Bool {
        guard let rir = rir else { return true }
        return rir >= 0
    }
}
