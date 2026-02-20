import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import {
  type User,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  getIdTokenResult,
} from 'firebase/auth'
import { auth } from '@/shared/lib/firebase'

interface AuthContextType {
  user: User | null
  uid: string | null
  email: string | null
  role: string | null
  clearance: string | null
  tenantId: string | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<User>
  signOut: () => Promise<void>
  refreshToken: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null)
  const [role, setRole] = useState<string | null>(null)
  const [clearance, setClearance] = useState<string | null>(null)
  const [tenantId, setTenantId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const extractClaims = async (currentUser: User) => {
    try {
      const tokenResult = await getIdTokenResult(currentUser)
      const claims = tokenResult.claims

      setRole((claims.role as string) || null)
      setClearance((claims.clearance_level as string) || null)
      setTenantId((claims.tenant_id as string) || null)
    } catch (error) {
      console.error('Error extracting claims:', error)
      setRole(null)
      setClearance(null)
      setTenantId(null)
    }
  }

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser: User | null) => {
      setUser(currentUser)
      
      if (currentUser) {
        await extractClaims(currentUser)
      } else {
        setRole(null)
        setClearance(null)
        setTenantId(null)
      }
      
      setLoading(false)
    })

    return () => unsubscribe()
  }, [])

  const signIn = async (email: string, password: string) => {
    try {
      console.log('[Auth] Calling signInWithEmailAndPassword...')
      const userCredential = await signInWithEmailAndPassword(auth, email, password)
      console.log('[Auth] Sign in successful, uid:', userCredential.user.uid)
      await extractClaims(userCredential.user)
      console.log('[Auth] Claims extracted successfully')
    } catch (error) {
      console.error('[Auth] Sign in error:', error)
      throw error
    }
  }

  const signUp = async (email: string, password: string) => {
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password)
      return userCredential.user
    } catch (error) {
      console.error('Sign up error:', error)
      throw error
    }
  }

  const signOut = async () => {
    try {
      await firebaseSignOut(auth)
      setRole(null)
      setClearance(null)
      setTenantId(null)
    } catch (error) {
      console.error('Sign out error:', error)
      throw error
    }
  }

  const refreshToken = async () => {
    if (user) {
      await extractClaims(user)
    }
  }

  const value: AuthContextType = {
    user,
    uid: user?.uid || null,
    email: user?.email || null,
    role,
    clearance,
    tenantId,
    loading,
    signIn,
    signUp,
    signOut,
    refreshToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
