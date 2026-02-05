//
//  WorkoutViewModel.swift
//  workout tracker app
//
//  Created by Claude on 26.01.2026.
//

import Foundation
import Combine

@MainActor
class WorkoutViewModel: ObservableObject {
    // MARK: - Published Properties
    @Published var workouts: [Workout] = []
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?

    // MARK: - Services
    private let supabaseService = SupabaseService.shared

    // MARK: - Lifecycle
    func loadWorkouts() async {
        isLoading = true
        errorMessage = nil

        do {
            workouts = try await supabaseService.fetchWorkouts()
        } catch {
            errorMessage = "Failed to load workouts: \(error.localizedDescription)"
        }

        isLoading = false
    }

    func deleteWorkout(_ workout: Workout) async {
        errorMessage = nil

        do {
            try await supabaseService.deleteWorkout(workoutId: workout.id)
            // Remove from local array
            workouts.removeAll { $0.id == workout.id }
        } catch {
            errorMessage = "Failed to delete workout: \(error.localizedDescription)"
        }
    }

    func createTestWorkout() async {
        isLoading = true
        errorMessage = nil

        do {
            // Create a test workout
            let workout = Workout(
                userId: supabaseService.currentUser?.id ?? UUID(),
                date: Date(),
                notes: "Test workout",
                duration: 3600
            )

            let exercises: [Exercise] = [
                Exercise(
                    workoutId: workout.id,
                    name: "Bench Press",
                    exerciseOrder: 1,
                    sets: [
                        WorkoutSet(exerciseId: UUID(), setNumber: 1, reps: 10, weight: 80, rpe: 7, rir: 3),
                        WorkoutSet(exerciseId: UUID(), setNumber: 2, reps: 10, weight: 80, rpe: 8, rir: 2),
                        WorkoutSet(exerciseId: UUID(), setNumber: 3, reps: 8, weight: 85, rpe: 9, rir: 1)
                    ]
                ),
                Exercise(
                    workoutId: workout.id,
                    name: "Squat",
                    exerciseOrder: 2,
                    sets: [
                        WorkoutSet(exerciseId: UUID(), setNumber: 1, reps: 12, weight: 100, rpe: 7, rir: 3),
                        WorkoutSet(exerciseId: UUID(), setNumber: 2, reps: 10, weight: 110, rpe: 8, rir: 2)
                    ]
                )
            ]

            let createdWorkout = try await supabaseService.createWorkout(workout, exercises: exercises)
            workouts.insert(createdWorkout, at: 0)
        } catch {
            errorMessage = "Failed to create workout: \(error.localizedDescription)"
        }

        isLoading = false
    }
}
