//
//  SupabaseService.swift
//  workout tracker app
//
//  Created by Claude on 25.01.2026.
//

import Foundation
import Combine
import Supabase

/// Service for interacting with Supabase backend
/// Handles authentication and CRUD operations for workouts
class SupabaseService: ObservableObject {

    // MARK: - Singleton
    static let shared = SupabaseService()

    // MARK: - Properties
    let client: SupabaseClient

    @Published var currentUser: User?
    @Published var isAuthenticated = false

    // MARK: - Initialization
    private init() {
        // Initialize Supabase client
        self.client = SupabaseClient(
            supabaseURL: URL(string: Config.supabaseURL)!,
            supabaseKey: Config.supabaseAnonKey
        )

        // Check if user is already logged in
        Task {
            await checkCurrentSession()
        }
    }

    // MARK: - Authentication

    /// Check if there's an active session
    func checkCurrentSession() async {
        do {
            let session = try await client.auth.session
            let user = session.user
            try await fetchUserProfile(userId: user.id)
            await MainActor.run {
                self.isAuthenticated = true
            }
        } catch {
            if Config.enableDebugLogging {
                print("No active session: \(error.localizedDescription)")
            }
            await MainActor.run {
                self.isAuthenticated = false
                self.currentUser = nil
            }
        }
    }

    /// Sign up new user with email and password
    func signUp(email: String, password: String) async throws -> User {
        let response = try await client.auth.signUp(email: email, password: password)

        guard let session = response.session else {
            throw NSError(domain: "SupabaseService", code: -1,
                         userInfo: [NSLocalizedDescriptionKey: "No session returned after signup"])
        }

        // Fetch user profile
        let user = try await fetchUserProfile(userId: session.user.id)

        await MainActor.run {
            self.currentUser = user
            self.isAuthenticated = true
        }

        return user
    }

    /// Sign in existing user
    func signIn(email: String, password: String) async throws -> User {
        let session = try await client.auth.signIn(email: email, password: password)

        // Fetch user profile
        let user = try await fetchUserProfile(userId: session.user.id)

        await MainActor.run {
            self.currentUser = user
            self.isAuthenticated = true
        }

        return user
    }

    /// Sign out current user
    func signOut() async throws {
        try await client.auth.signOut()

        await MainActor.run {
            self.currentUser = nil
            self.isAuthenticated = false
        }
    }

    /// Fetch user profile from database
    private func fetchUserProfile(userId: UUID) async throws -> User {
        let response: User = try await client.database
            .from("users")
            .select()
            .eq("id", value: userId.uuidString)
            .single()
            .execute()
            .value

        await MainActor.run {
            self.currentUser = response
        }

        return response
    }

    // MARK: - Workouts CRUD

    /// Fetch all workouts for current user
    func fetchWorkouts() async throws -> [Workout] {
        guard let userId = currentUser?.id else {
            throw NSError(domain: "SupabaseService", code: -1,
                         userInfo: [NSLocalizedDescriptionKey: "No authenticated user"])
        }

        let workouts: [Workout] = try await client.database
            .from("workouts")
            .select()
            .eq("user_id", value: userId.uuidString)
            .order("date", ascending: false)
            .execute()
            .value

        return workouts
    }

    /// Fetch single workout with exercises and sets
    func fetchWorkoutDetails(workoutId: UUID) async throws -> Workout {
        var workout: Workout = try await client.database
            .from("workouts")
            .select()
            .eq("id", value: workoutId.uuidString)
            .single()
            .execute()
            .value

        // Fetch exercises for this workout
        let exercises = try await fetchExercises(workoutId: workoutId)

        // Fetch sets for each exercise
        var exercisesWithSets: [Exercise] = []
        for var exercise in exercises {
            let sets = try await fetchSets(exerciseId: exercise.id)
            exercise.sets = sets
            exercisesWithSets.append(exercise)
        }

        workout.exercises = exercisesWithSets

        return workout
    }

    /// Create new workout with exercises and sets
    func createWorkout(_ workout: Workout, exercises: [Exercise]) async throws -> Workout {
        guard let userId = currentUser?.id else {
            throw NSError(domain: "SupabaseService", code: -1,
                         userInfo: [NSLocalizedDescriptionKey: "No authenticated user"])
        }

        // Create workout
        let createdWorkout: Workout = try await client.database
            .from("workouts")
            .insert(workout)
            .select()
            .single()
            .execute()
            .value

        // Create exercises
        var createdExercises: [Exercise] = []
        for var exercise in exercises {
            exercise.workoutId = createdWorkout.id
            let createdExercise = try await createExercise(exercise)

            // Create sets for this exercise
            if let sets = exercise.sets {
                var createdSets: [WorkoutSet] = []
                for var set in sets {
                    set.exerciseId = createdExercise.id
                    let createdSet = try await createSet(set)
                    createdSets.append(createdSet)
                }
                var exerciseWithSets = createdExercise
                exerciseWithSets.sets = createdSets
                createdExercises.append(exerciseWithSets)
            } else {
                createdExercises.append(createdExercise)
            }
        }

        var workoutWithData = createdWorkout
        workoutWithData.exercises = createdExercises

        return workoutWithData
    }

    /// Update workout
    func updateWorkout(_ workout: Workout) async throws -> Workout {
        let updated: Workout = try await client.database
            .from("workouts")
            .update(workout)
            .eq("id", value: workout.id.uuidString)
            .select()
            .single()
            .execute()
            .value

        return updated
    }

    /// Delete workout
    func deleteWorkout(workoutId: UUID) async throws {
        try await client.database
            .from("workouts")
            .delete()
            .eq("id", value: workoutId.uuidString)
            .execute()
    }

    // MARK: - Exercises CRUD

    /// Fetch exercises for a workout
    private func fetchExercises(workoutId: UUID) async throws -> [Exercise] {
        let exercises: [Exercise] = try await client.database
            .from("exercises")
            .select()
            .eq("workout_id", value: workoutId.uuidString)
            .order("exercise_order", ascending: true)
            .execute()
            .value

        return exercises
    }

    /// Create exercise
    private func createExercise(_ exercise: Exercise) async throws -> Exercise {
        let created: Exercise = try await client.database
            .from("exercises")
            .insert(exercise)
            .select()
            .single()
            .execute()
            .value

        return created
    }

    /// Update exercise
    func updateExercise(_ exercise: Exercise) async throws -> Exercise {
        let updated: Exercise = try await client.database
            .from("exercises")
            .update(exercise)
            .eq("id", value: exercise.id.uuidString)
            .select()
            .single()
            .execute()
            .value

        return updated
    }

    /// Delete exercise
    func deleteExercise(exerciseId: UUID) async throws {
        try await client.database
            .from("exercises")
            .delete()
            .eq("id", value: exerciseId.uuidString)
            .execute()
    }

    // MARK: - Sets CRUD

    /// Fetch sets for an exercise
    private func fetchSets(exerciseId: UUID) async throws -> [WorkoutSet] {
        let sets: [WorkoutSet] = try await client.database
            .from("workout_sets")
            .select()
            .eq("exercise_id", value: exerciseId.uuidString)
            .order("set_number", ascending: true)
            .execute()
            .value

        return sets
    }

    /// Create set
    private func createSet(_ set: WorkoutSet) async throws -> WorkoutSet {
        let created: WorkoutSet = try await client.database
            .from("workout_sets")
            .insert(set)
            .select()
            .single()
            .execute()
            .value

        return created
    }

    /// Update set
    func updateSet(_ set: WorkoutSet) async throws -> WorkoutSet {
        let updated: WorkoutSet = try await client.database
            .from("workout_sets")
            .update(set)
            .eq("id", value: set.id.uuidString)
            .select()
            .single()
            .execute()
            .value

        return updated
    }

    /// Delete set
    func deleteSet(setId: UUID) async throws {
        try await client.database
            .from("workout_sets")
            .delete()
            .eq("id", value: setId.uuidString)
            .execute()
    }
}
